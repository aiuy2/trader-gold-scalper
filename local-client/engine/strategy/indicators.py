"""indicators.py - plain-Python technical indicators (no pandas/numpy
dependency, since the mock/live tick loop and the backtest engine both
just need these on a list of closes). Kept dependency-free on purpose so
the desktop worker/EA and the backend can both import this without
pulling in a heavier data-science stack.
"""


def ema_series(values: list, period: int) -> list:
    """Full EMA series (same length as values, first `period-1` values are
    None). Used when you need the EMA at every point, not just the last."""
    if len(values) < period:
        return [None] * len(values)

    multiplier = 2 / (period + 1)
    result = [None] * (period - 1)
    sma = sum(values[:period]) / period
    result.append(sma)

    prev = sma
    for value in values[period:]:
        prev = (value - prev) * multiplier + prev
        result.append(prev)
    return result


def ema(values: list, period: int):
    """Latest EMA value only, or None if there isn't enough data."""
    series = ema_series(values, period)
    return series[-1] if series else None


def rsi(values: list, period: int = 14):
    """Standard Wilder's RSI over the last `period` changes. Returns None
    if there isn't enough data yet."""
    if len(values) < period + 1:
        return None

    gains, losses = [], []
    for i in range(1, period + 1):
        change = values[-period - 1 + i] - values[-period - 2 + i]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(highs: list, lows: list, closes: list, period: int = 14):
    """Average True Range - used to size stops proportionally to current
    volatility. All three lists must be the same length."""
    if len(closes) < period + 1:
        return None

    true_ranges = []
    for i in range(1, len(closes)):
        high_low = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i - 1])
        low_close = abs(lows[i] - closes[i - 1])
        true_ranges.append(max(high_low, high_close, low_close))

    recent = true_ranges[-period:]
    return sum(recent) / len(recent)
