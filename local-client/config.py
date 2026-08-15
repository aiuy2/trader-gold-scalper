"""config.py - local-client settings.

Reads from environment variables first (useful for a Windows service /
scheduled task where you set them once), falling back to a small JSON
config file next to the license cache
(~/.trader_gold_scalper/client_config.json) so a non-technical user can
just edit one file instead of dealing with env vars.

Required values:
    TRADER_API_URL       e.g. "https://api.yourdomain.com"
    TRADER_ACCESS_TOKEN  the same JWT the web app uses (see limitation
                          note in README.md - this MVP does not refresh
                          expired tokens automatically)

Optional:
    TRADER_MODE           "mock" (default, safe/no real MT5 needed) or "live"
    TRADER_SYMBOL          default "XAUUSD"
    TRADER_POLL_SECONDS    default 2.0
    TRADER_DEVICE_NAME     default the machine's hostname
"""
import json
import os
import platform

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".trader_gold_scalper")
CONFIG_FILE = os.path.join(CONFIG_DIR, "client_config.json")


def _load_file() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


class ClientConfig:
    def __init__(self):
        file_cfg = _load_file()

        self.api_url = os.environ.get("TRADER_API_URL", file_cfg.get("api_url"))
        self.access_token = os.environ.get("TRADER_ACCESS_TOKEN", file_cfg.get("access_token"))
        self.mode = os.environ.get("TRADER_MODE", file_cfg.get("mode", "mock"))
        self.symbol = os.environ.get("TRADER_SYMBOL", file_cfg.get("symbol", "XAUUSD"))
        self.poll_seconds = float(os.environ.get("TRADER_POLL_SECONDS", file_cfg.get("poll_seconds", 2.0)))
        self.device_name = os.environ.get("TRADER_DEVICE_NAME", file_cfg.get("device_name", platform.node()))

        # MT5 terminal login, only needed when mode == "live"
        self.mt5_login = os.environ.get("TRADER_MT5_LOGIN", file_cfg.get("mt5_login"))
        self.mt5_password = os.environ.get("TRADER_MT5_PASSWORD", file_cfg.get("mt5_password"))
        self.mt5_server = os.environ.get("TRADER_MT5_SERVER", file_cfg.get("mt5_server"))

    def validate(self) -> list:
        """Returns a list of human-readable problems, empty if config is usable."""
        problems = []
        if not self.api_url:
            problems.append("TRADER_API_URL is not set (env var or client_config.json)")
        if not self.access_token:
            problems.append("TRADER_ACCESS_TOKEN is not set (env var or client_config.json)")
        if self.mode not in ("mock", "live"):
            problems.append(f"TRADER_MODE must be 'mock' or 'live', got {self.mode!r}")
        if self.mode == "live" and not all([self.mt5_login, self.mt5_password, self.mt5_server]):
            problems.append("mode=live requires TRADER_MT5_LOGIN, TRADER_MT5_PASSWORD, TRADER_MT5_SERVER")
        return problems

    @property
    def ws_url(self) -> str:
        """Derives the ws(s):// URL for /ws from the http(s) api_url."""
        scheme = "wss" if self.api_url.startswith("https") else "ws"
        host = self.api_url.split("://", 1)[-1].rstrip("/")
        return f"{scheme}://{host}/ws?token={self.access_token}"


def write_example_file() -> str:
    """Writes a template config file the user can fill in by hand. Returns the path."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        template = {
            "api_url": "https://api.yourdomain.com",
            "access_token": "PASTE_YOUR_ACCESS_TOKEN_HERE",
            "mode": "mock",
            "symbol": "XAUUSD",
            "poll_seconds": 2.0,
            "device_name": platform.node(),
            "mt5_login": None,
            "mt5_password": None,
            "mt5_server": None,
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
            json.dump(template, fh, indent=2, ensure_ascii=False)
    return CONFIG_FILE
