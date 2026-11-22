"""Plain domain objects shared by every layer (no database or web dependencies)."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Signal:
    asset: str
    strategy: str
    direction: str  # "BULLISH" or "BEARISH"
    price: float
    bar_time: datetime  # timestamp of the price bar that triggered the signal
    # Indicator values at signal time. Phase 2 feeds this to the AI explainer.
    context: dict = field(default_factory=dict)

    @property
    def dedupe_key(self) -> str:
        """Same asset + strategy + direction + bar always yields the same key."""
        return f"{self.asset}|{self.strategy}|{self.direction}|{self.bar_time.isoformat()}"


@dataclass(frozen=True)
class Subscription:
    user_id: int
    asset: str
    channels: tuple[str, ...] = ("in_app",)


# Pre-seeded users stand in for real login in Phase 1.
DEMO_USERS: dict[str, list[str]] = {
    "alice": ["NIFTY", "BITCOIN"],
    "bob": ["GOLD", "SENSEX", "BITCOIN"],
    "carol": ["BANKNIFTY", "NIFTY"],
}
