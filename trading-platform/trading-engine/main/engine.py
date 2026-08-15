"""engine.py - the trading loop. Pulls price history from a connector
(mock or live MT5), asks the strategy for a signal, checks the risk
manager's circuit breakers, opens/manages one position at a time, and
closes it when price touches its stop-loss or take-profit.

Consumed by backend/services/bot_service.py, which runs engine.run() in a
background thread per user and mirrors each yielded outcome into the
database. Also reusable directly (see backtest/engine/backtest_engine.py)
against historical data instead of live/mock ticks.
"""
import json
import os
import time

from mt5.connector import MockMT5Connector
from risk.risk_manager import RiskManager
from strategy.scalping_strategy import ScalpingStrategy
from protection.mt5_monitor import is_connector_healthy

_DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "risk.json")


def _load_default_config() -> dict:
    with open(_DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


class TradingEngine:
    def __init__(self, connector=None, symbol: str = "XAUUSD", config: dict = None):
        self.connector = connector or MockMT5Connector(symbol=symbol)
        self.symbol = symbol
        self.risk_cfg = config or _load_default_config()
        self.risk_manager = RiskManager(self.risk_cfg)
        self.strategy = ScalpingStrategy.from_config(self.risk_cfg)

        self._open_position = None  # {"ticket","direction","lot","entry_price","stop_loss","take_profit"}
        self._price_history_len = 100

    # -- position lifecycle -------------------------------------------
    def _check_open_position(self, current_price: float):
        """Closes the open position if price has touched its SL or TP.
        Returns a "closed_trade" outcome dict, or None if still open."""
        pos = self._open_position
        if pos is None:
            return None

        hit_tp = (
            (pos["direction"] == "buy" and current_price >= pos["take_profit"]) or
            (pos["direction"] == "sell" and current_price <= pos["take_profit"])
        )
        hit_sl = (
            (pos["direction"] == "buy" and current_price <= pos["stop_loss"]) or
            (pos["direction"] == "sell" and current_price >= pos["stop_loss"])
        )
        if not (hit_tp or hit_sl):
            return None

        exit_price = pos["take_profit"] if hit_tp else pos["stop_loss"]
        close_result = self.connector.close_order(pos["ticket"], exit_price)

        contract_size = getattr(self.connector, "CONTRACT_SIZE", 100)
        direction_sign = 1 if pos["direction"] == "buy" else -1
        pnl = direction_sign * (exit_price - pos["entry_price"]) * pos["lot"] * contract_size

        self.risk_manager.register_trade_result(pnl)
        if hasattr(self.connector, "apply_pnl"):
            self.connector.apply_pnl(pnl)

        self._open_position = None
        return {
            "action": "closed_trade",
            "reason": "take_profit" if hit_tp else "stop_loss",
            "direction": pos["direction"],
            "ticket": pos["ticket"],
            "pnl": round(pnl, 2),
            "close_result": close_result,
        }

    def _try_open_position(self):
        prices = self.connector.get_price_history(self._price_history_len)
        current_price = prices[-1] if prices else self.connector.get_current_price()

        account_info = self.connector.get_account_info()
        allowed, reason = self.risk_manager.can_trade(account_info)
        if not allowed:
            return {"action": "blocked_by_risk", "reason": reason}

        direction = self.strategy.generate_signal(prices)
        if direction is None:
            return {"action": "no_signal"}

        trade_params = self.risk_manager.compute_trade_params(direction, current_price)
        order_result = self.connector.place_order(
            direction=direction,
            lot=trade_params["lot"],
            stop_loss=trade_params["stop_loss"],
            take_profit=trade_params["take_profit"],
        )

        if order_result.get("success"):
            self._open_position = {
                "ticket": order_result["ticket"],
                "direction": direction,
                "lot": trade_params["lot"],
                "entry_price": order_result["entry_price"],
                "stop_loss": trade_params["stop_loss"],
                "take_profit": trade_params["take_profit"],
            }

        return {
            "action": "opened_trade" if order_result.get("success") else "order_failed",
            "direction": direction,
            "trade_params": trade_params,
            "order_result": order_result,
        }

    # -- main loop ------------------------------------------------------
    def run(self, iterations: int = None, sleep_seconds: float = 2.0):
        """Generator - yields one outcome dict per iteration. iterations=None
        runs until the caller stops iterating (e.g. bot_service.py's stop
        flag) or the connector goes unhealthy."""
        count = 0
        while iterations is None or count < iterations:
            if not is_connector_healthy(self.connector):
                yield {"action": "connector_unhealthy"}
                if sleep_seconds:
                    time.sleep(sleep_seconds)
                count += 1
                continue

            current_price = self.connector.get_current_price()
            closed_outcome = self._check_open_position(current_price)
            if closed_outcome is not None:
                yield closed_outcome
            elif self._open_position is not None:
                yield {"action": "position_open", "ticket": self._open_position["ticket"]}
            else:
                yield self._try_open_position()

            count += 1
            if sleep_seconds:
                time.sleep(sleep_seconds)

    def status(self) -> dict:
        return {
            "symbol": self.symbol,
            "open_position": self._open_position,
            "risk": self.risk_manager.status(),
            "account": self.connector.get_account_info(),
        }
