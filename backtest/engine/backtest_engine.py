"""backtest_engine.py - orchestrates a full backtest run: loads historical
bars, builds an ExecutionSimulator + the real trading-platform
TradingEngine (same strategy/risk code that runs live), drives it with
BacktestSimulator, and computes summary metrics + a report.

Usage:
    from backtest_engine import BacktestEngine
    result = BacktestEngine(csv_path="backtest/historical-data/XAUUSD_M1_sample.csv").run()
    print(result["metrics"])

Historical data format (CSV, header required):
    time,open,high,low,close
    2024-01-02T00:00:00,2062.30,2063.10,2061.80,2062.90
    ...
Only `close` is used by the current strategy/execution model; open/high/low
are accepted for forward-compatibility (e.g. an ATR-based strategy) and
may be omitted if unavailable - see load_bars_from_csv.
"""
import csv
import json
import os
import sys
from datetime import datetime, timezone

_TRADING_ENGINE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "trading-platform", "trading-engine")
)
if _TRADING_ENGINE_PATH not in sys.path:
    sys.path.insert(0, _TRADING_ENGINE_PATH)

# So `simulator` / `execution_simulator` resolve as top-level modules even
# when this file is imported from elsewhere (e.g. `from backtest.engine...`)
# rather than run directly from this directory.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from main.engine import TradingEngine  # noqa: E402

from simulator import BacktestSimulator  # noqa: E402
from execution_simulator import ExecutionSimulator  # noqa: E402

_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
_REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")


def load_bars_from_csv(csv_path: str) -> list:
    bars = []
    with open(csv_path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            close = float(row["close"])
            bars.append({
                "time": row.get("time"),
                "open": float(row["open"]) if row.get("open") else close,
                "high": float(row["high"]) if row.get("high") else close,
                "low": float(row["low"]) if row.get("low") else close,
                "close": close,
            })
    return bars


def _compute_metrics(outcomes: list, starting_balance: float, ending_balance: float) -> dict:
    closed = [o for o in outcomes if o["action"] == "closed_trade"]
    wins = [t for t in closed if t["pnl"] > 0]
    losses = [t for t in closed if t["pnl"] <= 0]

    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))

    # Max drawdown from the running equity curve implied by trade order.
    running = starting_balance
    peak = starting_balance
    max_drawdown = 0.0
    for t in closed:
        running += t["pnl"]
        peak = max(peak, running)
        max_drawdown = max(max_drawdown, peak - running)

    return {
        "total_trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(100 * len(wins) / len(closed), 2) if closed else 0.0,
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else None,
        "net_pnl": round(ending_balance - starting_balance, 2),
        "starting_balance": starting_balance,
        "ending_balance": ending_balance,
        "max_drawdown": round(max_drawdown, 2),
    }


class BacktestEngine:
    def __init__(self, csv_path: str, symbol: str = "XAUUSD",
                 starting_balance: float = 10_000.0,
                 spread_pips: float = 3.0, slippage_pips: float = 1.0,
                 config: dict = None):
        self.csv_path = csv_path
        self.symbol = symbol
        self.starting_balance = starting_balance
        self.spread_pips = spread_pips
        self.slippage_pips = slippage_pips
        self.config = config

    def run(self, save: bool = True) -> dict:
        bars = load_bars_from_csv(self.csv_path)
        connector = ExecutionSimulator(
            bars, symbol=self.symbol, starting_balance=self.starting_balance,
            spread_pips=self.spread_pips, slippage_pips=self.slippage_pips,
        )
        engine = TradingEngine(connector=connector, symbol=self.symbol, config=self.config)
        outcomes = BacktestSimulator(engine, connector).run()

        metrics = _compute_metrics(outcomes, self.starting_balance, connector.balance)
        result = {
            "symbol": self.symbol,
            "csv_path": self.csv_path,
            "bar_count": len(bars),
            "run_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "trades": [o for o in outcomes if o["action"] == "closed_trade"],
        }

        if save:
            self._save(result)
        return result

    def _save(self, result: dict):
        os.makedirs(_RESULTS_DIR, exist_ok=True)
        os.makedirs(_REPORTS_DIR, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        results_path = os.path.join(_RESULTS_DIR, f"{self.symbol}_{stamp}.json")
        with open(results_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, default=str)

        report_path = os.path.join(_REPORTS_DIR, f"{self.symbol}_{stamp}.md")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write(self._render_report(result))

    @staticmethod
    def _render_report(result: dict) -> str:
        m = result["metrics"]
        lines = [
            f"# Backtest report - {result['symbol']}",
            "",
            f"- Data: `{result['csv_path']}` ({result['bar_count']} bars)",
            f"- Run at: {result['run_at']}",
            "",
            "## Metrics",
            "",
            f"- Total trades: {m['total_trades']}",
            f"- Win rate: {m['win_rate_pct']}%  ({m['wins']}W / {m['losses']}L)",
            f"- Net P&L: {m['net_pnl']} (start {m['starting_balance']} -> end {m['ending_balance']})",
            f"- Profit factor: {m['profit_factor']}",
            f"- Max drawdown: {m['max_drawdown']}",
        ]
        return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run a TRADER GOLD SCALPER backtest.")
    parser.add_argument("csv_path", help="Path to historical OHLC CSV data.")
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--balance", type=float, default=10_000.0)
    parser.add_argument("--config", default=None,
                         help="Path to a risk.json-shaped strategy preset (see backtest/strategies/).")
    args = parser.parse_args()

    config = None
    if args.config:
        with open(args.config, "r", encoding="utf-8") as fh:
            config = json.load(fh)

    outcome = BacktestEngine(
        args.csv_path, symbol=args.symbol, starting_balance=args.balance, config=config,
    ).run()
    print(json.dumps(outcome["metrics"], indent=2))
