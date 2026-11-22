"""Runtime settings, read from environment variables (see .env.example)."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    data_provider: str  # "synthetic" or "yfinance"
    poll_interval_seconds: int
    fast_ma: int
    slow_ma: int


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./market_signals.db"),
        data_provider=os.getenv("DATA_PROVIDER", "synthetic"),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "300")),
        fast_ma=int(os.getenv("FAST_MA", "20")),
        slow_ma=int(os.getenv("SLOW_MA", "50")),
    )
