"""risk_manager.py - position sizing, stop-loss/take-profit distances, and
the circuit breakers (max daily loss, max consecutive losses) that stop
the engine from trading regardless of what the strategy signals.

Config shape (see config/risk.json, and how backend/services/bot_service.py
overlays a user's own settings on top of it):

    {"risk": {"fixed_lot": 0.01, "risk_percent": 1.0,
               "max_daily_loss_pct": 5.0, "max_consecutive_losses": 3,
               "stop_loss_pips": 150, "take_profit_pips": 300,
               "pip_size": 0.1}}
"""
from datetime import date


class RiskManager:
    def __init__(self, config: dict):
        risk_cfg = (config or {}).get("risk", {})
        self.fixed_lot = risk_cfg.get("fixed_lot", 0.01)
        self.risk_percent = risk_cfg.get("risk_percent", 1.0)
        self.max_daily_loss_pct = risk_cfg.get("max_daily_loss_pct", 5.0)
        self.max_consecutive_losses = risk_cfg.get("max_consecutive_losses", 3)
        self.stop_loss_pips = risk_cfg.get("stop_loss_pips", 150)
        self.take_profit_pips = risk_cfg.get("take_profit_pips", 300)
        self.pip_size = risk_cfg.get("pip_size", 0.1)

        self._consecutive_losses = 0
        self._daily_pnl = 0.0
        self._daily_start_balance = None
        self._current_day = None

    # -- circuit breakers --------------------------------------------
    def _roll_day_if_needed(self, balance: float):
        today = date.today()
        if self._current_day != today:
            self._current_day = today
            self._daily_start_balance = balance
            self._daily_pnl = 0.0

    def can_trade(self, account_info: dict) -> tuple:
        """Returns (allowed: bool, reason: str | None)."""
        balance = account_info.get("balance", 0) if account_info else 0
        self._roll_day_if_needed(balance)

        if self._consecutive_losses >= self.max_consecutive_losses:
            return False, "max_consecutive_losses_reached"

        if self._daily_start_balance:
            loss_limit = -(self.max_daily_loss_pct / 100.0) * self._daily_start_balance
            if self._daily_pnl <= loss_limit:
                return False, "max_daily_loss_reached"

        return True, None

    def register_trade_result(self, pnl: float) -> None:
        self._daily_pnl += pnl
        if pnl < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0

    # -- sizing / SL-TP -------------------------------------------------
    def compute_trade_params(self, direction: str, entry_price: float) -> dict:
        sl_distance = self.stop_loss_pips * self.pip_size
        tp_distance = self.take_profit_pips * self.pip_size

        if direction == "buy":
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        else:
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance

        return {
            "lot": self.fixed_lot,
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
        }

    def status(self) -> dict:
        return {
            "consecutive_losses": self._consecutive_losses,
            "daily_pnl": round(self._daily_pnl, 2),
            "max_consecutive_losses": self.max_consecutive_losses,
            "max_daily_loss_pct": self.max_daily_loss_pct,
        }
