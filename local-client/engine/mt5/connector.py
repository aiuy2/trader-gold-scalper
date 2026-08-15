"""connector.py - MT5 connector implementations. Every connector (mock or
live) exposes the same duck-typed interface so main/engine.py, the backend
(services/bot_service.py) and monitoring (monitoring/health/mt5_health.py)
can all work against either one without caring which:

    get_price_history(count) -> list[float]   (most recent last)
    get_current_price()       -> float
    get_account_info()        -> dict (balance, equity, currency, ...)
    place_order(direction, lot, stop_loss, take_profit) -> dict
    close_order(ticket, exit_price)                     -> dict
"""
import random
from abc import ABC, abstractmethod


class MT5ConnectorBase(ABC):
    symbol: str

    @abstractmethod
    def get_price_history(self, count: int = 50) -> list:
        ...

    @abstractmethod
    def get_current_price(self) -> float:
        ...

    @abstractmethod
    def get_account_info(self) -> dict:
        ...

    @abstractmethod
    def place_order(self, direction: str, lot: float, stop_loss: float, take_profit: float) -> dict:
        ...

    @abstractmethod
    def close_order(self, ticket: int, exit_price: float) -> dict:
        ...


class MockMT5Connector(MT5ConnectorBase):
    """Simulated broker connection - no MetaTrader5 terminal required.
    Generates a bounded random walk around a realistic XAUUSD price so the
    full app flow (start bot -> see trades -> stop bot) works out of the
    box in dev/demo/backtest-smoke-test contexts. Used by default whenever
    USE_MOCK_MT5=true (see backend/app/config.py) or mode="mock".
    """

    CONTRACT_SIZE = 100  # oz of gold per standard lot, used for mock P&L only

    def __init__(self, symbol: str = "XAUUSD", starting_price: float = 2400.0,
                 starting_balance: float = 10_000.0, seed: int = None):
        self.symbol = symbol
        self.price = starting_price
        self.balance = starting_balance
        self.equity = starting_balance
        self.history = [starting_price]
        self._ticket_counter = 100_000
        self._rng = random.Random(seed)

    def _step_price(self) -> float:
        # Small gaussian step plus an occasional bigger "spike" tick, loosely
        # mimicking gold's bursts of volatility around news.
        change = self._rng.gauss(0, 0.35)
        if self._rng.random() < 0.03:
            change += self._rng.choice([-1, 1]) * self._rng.uniform(1.0, 3.0)
        self.price = round(max(0.01, self.price + change), 2)
        self.history.append(self.price)
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
        return self.price

    def get_price_history(self, count: int = 50) -> list:
        self._step_price()
        return list(self.history[-count:])

    def get_current_price(self) -> float:
        return self.price

    def get_account_info(self) -> dict:
        return {
            "balance": round(self.balance, 2),
            "equity": round(self.equity, 2),
            "currency": "USD",
            "leverage": 100,
            "server": "MockServer-Demo",
            "symbol": self.symbol,
        }

    def place_order(self, direction: str, lot: float, stop_loss: float, take_profit: float) -> dict:
        self._ticket_counter += 1
        return {
            "success": True,
            "ticket": self._ticket_counter,
            "entry_price": self.price,
            "direction": direction,
            "lot": lot,
        }

    def close_order(self, ticket: int, exit_price: float) -> dict:
        return {"success": True, "ticket": ticket, "exit_price": exit_price}

    def apply_pnl(self, pnl: float) -> None:
        """Internal - lets the engine reflect a closed trade's P&L in the
        mock account balance/equity so /bot/status and account_service
        figures move realistically."""
        self.balance = round(self.balance + pnl, 2)
        self.equity = self.balance


class LiveMT5Connector(MT5ConnectorBase):
    """Real broker connection via the MetaTrader5 Python package. Only
    importable/usable on Windows with a running MT5 terminal (see
    requirements.txt) - kept isolated here so the rest of the codebase
    (including this whole package's mock path) never needs MetaTrader5
    installed to run.

    Wire up with real credentials from backend/services/account_service.py
    (AccountService.get_credentials), which decrypts the stored MT5
    password just-in-time for login and never logs/persists it in
    plaintext.
    """

    def __init__(self, symbol: str, login: str, password: str, server: str):
        try:
            import MetaTrader5 as mt5
        except ImportError as exc:
            raise RuntimeError(
                "MetaTrader5 package not available - live trading requires "
                "running on Windows with a MetaTrader5 terminal installed."
            ) from exc

        self._mt5 = mt5
        self.symbol = symbol
        if not mt5.initialize(login=int(login), password=password, server=server):
            raise RuntimeError(f"MT5 initialize() failed: {mt5.last_error()}")

    def get_price_history(self, count: int = 50) -> list:
        rates = self._mt5.copy_rates_from_pos(self.symbol, self._mt5.TIMEFRAME_M1, 0, count)
        if rates is None:
            return []
        return [float(r["close"]) for r in rates]

    def get_current_price(self) -> float:
        tick = self._mt5.symbol_info_tick(self.symbol)
        if tick is None:
            raise RuntimeError(f"No tick data for {self.symbol}")
        return float(tick.bid)

    def get_account_info(self) -> dict:
        info = self._mt5.account_info()
        if info is None:
            return None
        return {
            "balance": info.balance,
            "equity": info.equity,
            "currency": info.currency,
            "leverage": info.leverage,
            "server": info.server,
            "symbol": self.symbol,
        }

    def place_order(self, direction: str, lot: float, stop_loss: float, take_profit: float) -> dict:
        order_type = self._mt5.ORDER_TYPE_BUY if direction == "buy" else self._mt5.ORDER_TYPE_SELL
        price = self.get_current_price()
        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": lot,
            "type": order_type,
            "price": price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 20,
            "magic": 990011,
            "comment": "TRADER GOLD SCALPER",
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._mt5.ORDER_FILLING_IOC,
        }
        result = self._mt5.order_send(request)
        if result is None or result.retcode != self._mt5.TRADE_RETCODE_DONE:
            return {"success": False, "error": str(result)}
        return {
            "success": True,
            "ticket": result.order,
            "entry_price": result.price,
            "direction": direction,
            "lot": lot,
        }

    def close_order(self, ticket: int, exit_price: float = None) -> dict:
        positions = self._mt5.positions_get(ticket=ticket)
        if not positions:
            return {"success": False, "error": "position_not_found"}
        position = positions[0]
        close_type = self._mt5.ORDER_TYPE_SELL if position.type == self._mt5.ORDER_TYPE_BUY else self._mt5.ORDER_TYPE_BUY
        price = exit_price or self.get_current_price()
        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": position.volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 990011,
            "comment": "TRADER GOLD SCALPER close",
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._mt5.ORDER_FILLING_IOC,
        }
        result = self._mt5.order_send(request)
        if result is None or result.retcode != self._mt5.TRADE_RETCODE_DONE:
            return {"success": False, "error": str(result)}
        return {"success": True, "ticket": ticket, "exit_price": price}
