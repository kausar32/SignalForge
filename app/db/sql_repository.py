"""SQLAlchemy implementation of the Repository interface, plus helpers the API needs."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..domain import Signal, Subscription
from .models import NotificationRow, SignalRow, SubscriptionRow, UserRow


def _split(channels: str) -> tuple[str, ...]:
    return tuple(c for c in channels.split(",") if c)


class SqlRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # -- Repository interface ------------------------------------------------
    def save_signal(self, signal: Signal) -> int | None:
        row = SignalRow(
            asset=signal.asset,
            strategy=signal.strategy,
            direction=signal.direction,
            price=signal.price,
            bar_time=signal.bar_time,
            context=signal.context,
            dedupe_key=signal.dedupe_key,
        )
        self.session.add(row)
        try:
            self.session.commit()
        except IntegrityError:  # unique dedupe_key: this signal was already stored
            self.session.rollback()
            return None
        return row.id

    def subscriptions_for(self, asset: str) -> list[Subscription]:
        rows = self.session.scalars(select(SubscriptionRow).where(SubscriptionRow.asset == asset))
        return [Subscription(r.user_id, r.asset, _split(r.channels)) for r in rows]

    def add_notification(self, user_id: int, signal_id: int, channel: str) -> None:
        self.session.add(NotificationRow(user_id=user_id, signal_id=signal_id, channel=channel))
        self.session.commit()

    def list_signals(self, asset: str | None = None, limit: int = 50) -> list[dict]:
        stmt = select(SignalRow).order_by(SignalRow.id.desc()).limit(limit)
        if asset:
            stmt = stmt.where(SignalRow.asset == asset)
        return [
            {
                "id": r.id,
                "asset": r.asset,
                "strategy": r.strategy,
                "direction": r.direction,
                "price": r.price,
                "bar_time": r.bar_time.isoformat(),
                "context": r.context,
                "explanation": r.explanation,
            }
            for r in self.session.scalars(stmt)
        ]

    def list_notifications(self, user_id: int, limit: int = 50) -> list[dict]:
        stmt = (
            select(NotificationRow, SignalRow)
            .join(SignalRow, NotificationRow.signal_id == SignalRow.id)
            .where(NotificationRow.user_id == user_id)
            .order_by(NotificationRow.id.desc())
            .limit(limit)
        )
        return [
            {
                "signal_id": s.id,
                "channel": n.channel,
                "is_read": n.is_read,
                "asset": s.asset,
                "strategy": s.strategy,
                "direction": s.direction,
                "price": s.price,
                "bar_time": s.bar_time.isoformat(),
            }
            for n, s in self.session.execute(stmt)
        ]

    # -- helpers for the API and seeding --------------------------------------
    def user_exists(self, user_id: int) -> bool:
        return self.session.get(UserRow, user_id) is not None

    def get_or_create_user(self, name: str) -> int:
        user = self.session.scalars(select(UserRow).where(UserRow.name == name)).first()
        if user is None:
            user = UserRow(name=name)
            self.session.add(user)
            self.session.commit()
        return user.id

    def get_subscriptions(self, user_id: int) -> list[dict]:
        rows = self.session.scalars(
            select(SubscriptionRow).where(SubscriptionRow.user_id == user_id).order_by(SubscriptionRow.asset)
        )
        return [{"asset": r.asset, "channels": list(_split(r.channels))} for r in rows]

    def set_subscription(self, user_id: int, asset: str, channels: tuple[str, ...]) -> None:
        row = self.session.scalars(
            select(SubscriptionRow).where(
                SubscriptionRow.user_id == user_id, SubscriptionRow.asset == asset
            )
        ).first()
        if row is None:
            row = SubscriptionRow(user_id=user_id, asset=asset)
            self.session.add(row)
        row.channels = ",".join(channels)
        self.session.commit()

    def remove_subscription(self, user_id: int, asset: str) -> bool:
        row = self.session.scalars(
            select(SubscriptionRow).where(
                SubscriptionRow.user_id == user_id, SubscriptionRow.asset == asset
            )
        ).first()
        if row is None:
            return False
        self.session.delete(row)
        self.session.commit()
        return True
