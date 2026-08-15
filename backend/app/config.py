"""config.py - backend settings, loaded from environment variables (.env)."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Settings:
    DB_URL: str = os.getenv("DB_URL", "sqlite:///./trader_gold_scalper.db")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    API_URL: str = os.getenv("API_URL", "http://localhost:8000")
    USE_MOCK_MT5: bool = os.getenv("USE_MOCK_MT5", "true").lower() == "true"


settings = Settings()
