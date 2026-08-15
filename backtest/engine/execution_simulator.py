"""execution_simulator.py - fills orders against historical bars with a
configurable spread and slippage, exposing the exact same duck-typed
interface as mt5/connector.py's connectors (get_price_history,
get_current_price, get_account_info, place_order, close_order). This
means backtest_engine.py can hand this to the *same*
trading-platform/trading-engine TradingEngine used live/mock - the
strategy and risk logic under test are identical to what runs in
production, not a reimplementation that could quietly drift from it.
"""
import sys
import os

_TRADING_ENGINE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "trading-platform", "trading-engine")
)
if _TRADING_ENGINE_PATH not in sys.path:
    sys.path.insert(0, _TRADING_ENGINE_PATH)


class ExecutionSimulator:
    """A historical-data-backed stand-in for MT5ConnectorBase.

    bars: list of dicts with at least {"time", "open", "high", "low", "close"},
    oldest first. spread_pips / slippage_pips are applied in price units via
    pip_size (0.1 for XAUUSD-style quoting, matching risk.json's default).
    """

    CONTRACT_SIZE = 100

    def __init__(self, bars: list, symbol: str = "XAUUSD",
                 starting_balance: float = 10_000.0,
                 spread_pips: float = 3.0, slippage_pips: float = 1.0,
                 pip_size: float = 0.1, history_window: int = 100):
        if not bars:
            raise ValueError("ExecutionSimulator requires at least one historical bar.")
        self.bars = bars
        self.symbol = symbol
        self.balance = starting_balance
        self.equity = starting_balance
        self.spread = spread_pips * pip_size
        self.slippage = slippage_pips * pip_size
        self.history_window = history_window

        self._index = history_window if history_window < len(bars) else 0
        self._ticket_counter = 500_000
        self.closed_trades = []  # populated as the engine closes positions

    # -- iteration ------------------------------------------------------
    @property
    def finished(self) -> bool:
        return self._index >= len(self.bars) - 1

    def advance(self) -> bool:
        """Moves to the next historical bar. Returns False once data runs
        out (caller should stop the run loop)."""
        if self.finished:
            return False
        self._index += 1
        return True

    def current_bar(self) -> dict:
        return self.bars[self._index]

    # -- connector interface ---------------------------------------------
    def get_price_history(self, count: int = 50) -> list:
        start = max(0, self._index - count + 1)
        return [bar["close"] for bar in self.bars[start:self._index + 1]]

    def get_current_price(self) -> float:
        return self.bars[self._index]["close"]

    def get_account_info(self) -> dict:
        return {
            "balance": round(self.balance, 2),
            "equity": round(self.equity, 2),
            "currency": "USD",
            "leverage": 100,
            "server": "Backtest",
            "symbol": self.symbol,
        }

    def place_order(self, direction: str, lot: float, stop_loss: float, take_profit: float) -> dict:
        self._ticket_counter += 1
        mid = self.get_current_price()
        # buys fill at ask (mid + half-spread + slippage), sells at bid
        fill_price = (
            mid + self.spread / 2 + self.slippage if direction == "buy"
            else mid - self.spread / 2 - self.slippage
        )
        return {
            "success": True,
            "ticket": self._ticket_counter,
            "entry_price": round(fill_price, 2),
            "direction": direction,
            "lot": lot,
        }

    def close_order(self, ticket: int, exit_price: float) -> dict:
        self.closed_trades.append({
            "ticket": ticket,
            "exit_price": exit_price,
            "time": self.current_bar().get("time"),
        })
        return {"success": True, "ticket": ticket, "exit_price": exit_price}

    def apply_pnl(self, pnl: float) -> None:
        self.balance = round(self.balance + pnl, 2)
        self.equity = self.balance
