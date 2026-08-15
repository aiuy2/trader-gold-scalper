"""simulator.py - drives a TradingEngine bar-by-bar over historical data
via an ExecutionSimulator, without the live loop's sleep/health-check
overhead (see main/engine.py's run()). Intentionally calls the engine's
internal position-management methods directly rather than iterating
engine.run() itself, since run() is written for a real-time loop
(polling delay, connectivity checks) that doesn't apply when replaying
bars as fast as possible.
"""


class BacktestSimulator:
    def __init__(self, engine, connector):
        self.engine = engine
        self.connector = connector

    def run(self) -> list:
        """Runs until the connector's historical data is exhausted.
        Returns the list of outcome dicts, one per bar (same shape as
        main/engine.py's run() yields: opened_trade / closed_trade /
        no_signal / blocked_by_risk)."""
        outcomes = []
        while True:
            current_price = self.connector.get_current_price()

            closed = self.engine._check_open_position(current_price)
            if closed is not None:
                outcomes.append(closed)
            elif self.engine._open_position is None:
                outcomes.append(self.engine._try_open_position())
            else:
                outcomes.append({"action": "position_open"})

            if not self.connector.advance():
                break
        return outcomes
