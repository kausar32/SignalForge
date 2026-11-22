"""Seed demo users and subscriptions (stand-in for real login in Phase 1)."""

from sqlalchemy.orm import Session

from ..domain import DEMO_USERS
from .sql_repository import SqlRepository


def seed_demo(session: Session) -> None:
    repo = SqlRepository(session)
    for name, assets in DEMO_USERS.items():
        user_id = repo.get_or_create_user(name)
        for asset in assets:
            repo.set_subscription(user_id, asset, ("in_app",))
