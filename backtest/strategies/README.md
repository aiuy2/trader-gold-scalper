# Strategy presets

Each file here is a full `risk.json`-shaped config (same shape as
`trading-platform/trading-engine/config/risk.json`) so you can backtest
different risk/strategy tunings against the same historical data without
editing the engine's default config.

- `conservative.json` - smaller lot, tighter loss limits, slower EMAs
- `aggressive.json` - bigger lot, wider stops/targets, faster EMAs

Run with:

    python backtest_engine.py ../historical-data/XAUUSD_M1_sample.csv --config ../strategies/aggressive.json
