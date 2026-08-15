"""run.py - entry point for the local trading client.

Run this (as a plain process, a Windows scheduled task, or eventually a
Windows Service) on the SAME machine as the MT5 terminal. It:

  1. checks the license (license-system/, same rules as the backend)
  2. builds a connector (mock for testing, live MT5 for real trading)
  3. runs the trading engine loop locally
  4. reports each outcome to the backend over an outbound WebSocket so
     the web app keeps showing live status (see ws_client.py)
  5. refuses to open new trades whenever this machine has no internet
     route (see connectivity.py) - existing open positions stay
     protected by their SL/TP on the broker side regardless

This file is intentionally the only "wiring" module - engine/, the
license-system/, connectivity.py and ws_client.py all stay independent
and reusable on their own.
"""
import os
import sys
import time

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ENGINE_DIR = os.path.join(_THIS_DIR, "engine")
_LICENSE_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "license-system"))
for _p in (_ENGINE_DIR, _LICENSE_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from config import ClientConfig, write_example_file  # noqa: E402
from connectivity import ConnectivityGuard  # noqa: E402
from ws_client import WSReporter  # noqa: E402

from device_binding import LicenseGuard  # noqa: E402
from exceptions import LicenseError  # noqa: E402

from main.engine import TradingEngine  # noqa: E402
from mt5.connector import MockMT5Connector  # noqa: E402


def build_connector(cfg: ClientConfig):
    if cfg.mode == "mock":
        return MockMT5Connector(symbol=cfg.symbol)

    # Live mode - imported lazily since the MetaTrader5 package only
    # installs on Windows with a terminal present (see requirements.txt).
    from mt5.connector import LiveMT5Connector
    return LiveMT5Connector(
        symbol=cfg.symbol,
        login=cfg.mt5_login,
        password=cfg.mt5_password,
        server=cfg.mt5_server,
    )


def guarded_outcomes(engine: TradingEngine, connectivity: ConnectivityGuard, poll_seconds: float):
    """Wraps engine.run() so a single missing check - internet
    reachability - is enforced before the engine is ever allowed to take
    a step. If we're offline, the engine's generate_signal/place_order
    path is never reached, so no new trade can be opened.
    """
    engine_iter = engine.run(iterations=None, sleep_seconds=poll_seconds)
    while True:
        if not connectivity.is_online():
            yield {"action": "offline_paused"}
            time.sleep(poll_seconds)
            continue
        try:
            yield next(engine_iter)
        except StopIteration:
            return


def main():
    cfg = ClientConfig()
    problems = cfg.validate()
    if problems:
        example_path = write_example_file()
        print("Config problems:")
        for p in problems:
            print(f"  - {p}")
        print(f"\nEdit {example_path} and re-run, or set the TRADER_* env vars.")
        sys.exit(1)

    guard = LicenseGuard(api_url=cfg.api_url)
    try:
        license_data = guard.enforce(cfg.access_token, device_name=cfg.device_name, platform_name=sys.platform)
    except LicenseError as exc:
        print(f"License check failed, refusing to start: {exc}")
        sys.exit(1)
    print(f"License OK (plan={license_data.get('plan')}, device={guard.device_id[:8]}...)")

    connector = build_connector(cfg)
    engine = TradingEngine(connector=connector, symbol=cfg.symbol)
    connectivity = ConnectivityGuard(api_host=cfg.api_url.split("://", 1)[-1].split("/")[0])

    reporter = WSReporter(cfg.ws_url)
    reporter.start()

    print(f"Starting local trading client - mode={cfg.mode} symbol={cfg.symbol} poll={cfg.poll_seconds}s")
    print("Press Ctrl+C to stop.")
    try:
        for outcome in guarded_outcomes(engine, connectivity, cfg.poll_seconds):
            action = outcome.get("action")
            if action not in ("no_signal", "position_open"):
                print(outcome)
            reporter.report(action, {**outcome, "symbol": cfg.symbol, "mode": cfg.mode})
    except KeyboardInterrupt:
        print("\nStopping (user requested).")
    finally:
        reporter.stop()


if __name__ == "__main__":
    main()
