"""Storage interface used by the pipeline, plus an in-memory implementation.

The in-memory repository powers the zero-infrastructure demo and the unit tests.
The SQLAlchemy implementation lives in app/db/sql_repository.py.
"""

from typing import Protocol

from .domain import Signal, Subscription


class Repository(Protocol):
    def save_signal(self, signal: Signal) -> int | None:
        """Store a signal. Returns its id, or None if it already exists (duplicate)."""
        ...

    def subscriptions_for(self, asset: str) -> list[Subscription]: ...

    def add_notification(self, user_id: int, signal_id: int, channel: str) -> None: ...

    def list_signals(self, asset: str | None = None, limit: int = 50) -> list[dict]: ...

    def list_notifications(self, user_id: int, limit: int = 50) -> list[dict]: ...


class InMemoryRepository:
    def __init__(self) -> None:
        self._users: dict[int, str] = {}
        self._subs: list[Subscription] = []
        self._signals: list[dict] = []
        self._keys: set[str] = set()
        self._notifications: list[dict] = []

    # -- setup helpers (demo and tests) ------------------------------------
    def add_user(self, name: str) -> int:
        user_id = len(self._users) + 1
        self._users[user_id] = name
        return user_id

    def users(self) -> dict[int, str]:
        return dict(self._users)

    def subscribe(self, user_id: int, asset: str, channels: tuple[str, ...] = ("in_app",)) -> None:
        self._subs = [s for s in self._subs if not (s.user_id == user_id and s.asset == asset)]
        self._subs.append(Subscription(user_id, asset, channels))

    # -- Repository interface ------------------------------------------------
    def save_signal(self, signal: Signal) -> int | None:
        if signal.dedupe_key in self._keys:
            return None
        self._keys.add(signal.dedupe_key)
        signal_id = len(self._signals) + 1
        self._signals.append(
            {
                "id": signal_id,
                "asset": signal.asset,
                "strategy": signal.strategy,
                "direction": signal.direction,
                "price": signal.price,
                "bar_time": signal.bar_time.isoformat(),
                "context": signal.context,
                "explanation": None,
            }
        )
        return signal_id

    def subscriptions_for(self, asset: str) -> list[Subscription]:
        return [s for s in self._subs if s.asset == asset]

    def add_notification(self, user_id: int, signal_id: int, channel: str) -> None:
        self._notifications.append(
            {"user_id": user_id, "signal_id": signal_id, "channel": channel, "is_read": False}
        )

    def list_signals(self, asset: str | None = None, limit: int = 50) -> list[dict]:
        rows = [s for s in reversed(self._signals) if asset is None or s["asset"] == asset]
        return rows[:limit]

    def list_notifications(self, user_id: int, limit: int = 50) -> list[dict]:
        out = []
        for n in reversed(self._notifications):
            if n["user_id"] != user_id:
                continue
            signal = self._signals[n["signal_id"] - 1]
            out.append(
                {
                    "signal_id": n["signal_id"],
                    "channel": n["channel"],
                    "is_read": n["is_read"],
                    "asset": signal["asset"],
                    "strategy": signal["strategy"],
                    "direction": signal["direction"],
                    "price": signal["price"],
                    "bar_time": signal["bar_time"],
                }
            )
        return out[:limit]
