"""scalping_strategy.py - EMA-crossover entry filtered by RSI, tuned for
short-timeframe gold (XAUUSD) scalping:

  - a fast EMA crossing above the slow EMA is a buy signal, unless RSI
    already shows overbought (chasing a move that's about to stall)
  - a fast EMA crossing below the slow EMA is a sell signal, unless RSI
    already shows oversold

This is intentionally a simple, readable baseline strategy - swap it out
or extend it (add ATR-based confirmation, session filters, spread checks,
etc.) without touching main/engine.py, which only depends on
generate_signal(prices) -> "buy" | "sell" | None.
"""
from strategy.indicators import ema, rsi


class ScalpingStrategy:
    def __init__(self, fast_period: int = 8, slow_period: int = 21,
                 rsi_period: int = 14, rsi_overbought: float = 70,
                 rsi_oversold: float = 30):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold

    @classmethod
    def from_config(cls, config: dict) -> "ScalpingStrategy":
        cfg = (config or {}).get("strategy", {})
        return cls(
            fast_period=cfg.get("fast_ema_period", 8),
            slow_period=cfg.get("slow_ema_period", 21),
            rsi_period=cfg.get("rsi_period", 14),
            rsi_overbought=cfg.get("rsi_overbought", 70),
            rsi_oversold=cfg.get("rsi_oversold", 30),
        )

    def generate_signal(self, prices: list):
        """prices: recent closes, oldest first, current price last.
        Returns "buy", "sell", or None."""
        min_len = self.slow_period + 2
        if len(prices) < min_len:
            return None

        fast_now = ema(prices, self.fast_period)
        slow_now = ema(prices, self.slow_period)
        fast_prev = ema(prices[:-1], self.fast_period)
        slow_prev = ema(prices[:-1], self.slow_period)

        if None in (fast_now, slow_now, fast_prev, slow_prev):
            return None

        current_rsi = rsi(prices, self.rsi_period)
        if current_rsi is None:
            return None

        crossed_up = fast_prev <= slow_prev and fast_now > slow_now
        crossed_down = fast_prev >= slow_prev and fast_now < slow_now

        if crossed_up and current_rsi < self.rsi_overbought:
            return "buy"
        if crossed_down and current_rsi > self.rsi_oversold:
            return "sell"
        return None
