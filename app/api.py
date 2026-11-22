"""REST API. Run with: uvicorn app.api:create_app --factory --reload

Phase 1 has no login: the user id is part of the URL and demo users are pre-seeded.
"""

from collections.abc import Iterator

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import __version__
from .assets import ASSETS
from .config import get_settings
from .db.seed import seed_demo
from .db.session import init_db, make_engine, make_session_factory
from .db.sql_repository import SqlRepository
from .market_data import build_provider
from .notify import InAppChannel
from .pipeline import run_once
from .strategies import default_strategies

VALID_CHANNELS = {"in_app", "telegram"}  # telegram delivery arrives in a later phase


class SubscriptionIn(BaseModel):
    channels: list[str] = Field(default_factory=lambda: ["in_app"])


def create_app(database_url: str | None = None, init_schema: bool = False) -> FastAPI:
    settings = get_settings()
    engine = make_engine(database_url or settings.database_url)
    session_factory = make_session_factory(engine)
    if init_schema:
        init_db(engine)
        with session_factory() as session:
            seed_demo(session)

    app = FastAPI(title="MarketSignals AI", version=__version__)

    def get_repo() -> Iterator[SqlRepository]:
        with session_factory() as session:
            yield SqlRepository(session)

    def require_asset(asset: str) -> str:
        symbol = asset.upper()
        if symbol not in ASSETS:
            raise HTTPException(404, f"Unknown asset '{asset}'")
        return symbol

    def require_user(repo: SqlRepository, user_id: int) -> None:
        if not repo.user_exists(user_id):
            raise HTTPException(404, f"Unknown user {user_id}")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/assets")
    def list_assets() -> list[dict]:
        return [
            {"symbol": a.symbol, "name": a.name, "category": a.category} for a in ASSETS.values()
        ]

    @app.get("/signals")
    def list_signals(
        asset: str | None = None, limit: int = 50, repo: SqlRepository = Depends(get_repo)
    ) -> list[dict]:
        symbol = require_asset(asset) if asset else None
        return repo.list_signals(symbol, min(limit, 200))

    @app.get("/users/{user_id}/subscriptions")
    def get_subscriptions(user_id: int, repo: SqlRepository = Depends(get_repo)) -> list[dict]:
        require_user(repo, user_id)
        return repo.get_subscriptions(user_id)

    @app.put("/users/{user_id}/subscriptions/{asset}")
    def put_subscription(
        user_id: int, asset: str, body: SubscriptionIn, repo: SqlRepository = Depends(get_repo)
    ) -> dict:
        require_user(repo, user_id)
        symbol = require_asset(asset)
        invalid = set(body.channels) - VALID_CHANNELS
        if invalid or not body.channels:
            raise HTTPException(422, f"channels must be a non-empty subset of {sorted(VALID_CHANNELS)}")
        repo.set_subscription(user_id, symbol, tuple(body.channels))
        return {"user_id": user_id, "asset": symbol, "channels": body.channels}

    @app.delete("/users/{user_id}/subscriptions/{asset}")
    def delete_subscription(
        user_id: int, asset: str, repo: SqlRepository = Depends(get_repo)
    ) -> dict:
        require_user(repo, user_id)
        removed = repo.remove_subscription(user_id, require_asset(asset))
        return {"removed": removed}

    @app.get("/users/{user_id}/notifications")
    def get_notifications(
        user_id: int, limit: int = 50, repo: SqlRepository = Depends(get_repo)
    ) -> list[dict]:
        require_user(repo, user_id)
        return repo.list_notifications(user_id, min(limit, 200))

    @app.post("/pipeline/run")
    def trigger_pipeline(repo: SqlRepository = Depends(get_repo)) -> dict:
        """Run one pipeline pass on demand (the worker does this on a schedule)."""
        result = run_once(
            build_provider(settings.data_provider),
            default_strategies(settings),
            repo,
            {"in_app": InAppChannel(repo)},
        )
        return {
            "signals_created": len(result.created),
            "notifications": result.notifications,
            "errors": result.errors,
        }

    return app
