# Historical data

`XAUUSD_M1_sample.csv` is **synthetic** data (a seeded random walk shaped
like gold's tick behaviour) generated only so `backtest_engine.py` is
runnable out of the box with no external data source. It is not real
market data - do not draw conclusions about strategy performance from it.

For a real backtest, replace it with actual XAUUSD OHLC history (export
from your MT5 terminal's History Center, or a data vendor) in the same
CSV shape:

```
time,open,high,low,close
2024-01-02T00:00:00,2062.30,2063.10,2061.80,2062.90
```

`open`/`high`/`low` are optional (only `close` currently drives the
strategy/execution model) but keep the header either way.
