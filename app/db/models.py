"""SQLAlchemy models. Works on SQLite (local) and PostgreSQL (Docker Compose)."""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Phase 4


class SubscriptionRow(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "asset", name="uq_subscription_user_asset"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    asset: Mapped[str] = mapped_column(String(20), index=True)
    channels: Mapped[str] = mapped_column(String(100), default="in_app")  # comma separated


class SignalRow(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset: Mapped[str] = mapped_column(String(20), index=True)
    strategy: Mapped[str] = mapped_column(String(50))
    direction: Mapped[str] = mapped_column(String(10))
    price: Mapped[float] = mapped_column(Float)
    bar_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Phase 2: AI explainer
    dedupe_key: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class NotificationRow(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"))
    channel: Mapped[str] = mapped_column(String(20))
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
