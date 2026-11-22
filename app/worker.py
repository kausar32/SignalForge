"""Scheduled worker: runs the pipeline every POLL_INTERVAL_SECONDS.

Run with: python -m app.worker
"""

import logging
import signal
import threading

from .config import get_settings
from .db.session import make_engine, make_session_factory
from .db.sql_repository import SqlRepository
from .market_data import build_provider
from .notify import InAppChannel
from .pipeline import run_once
from .strategies import default_strategies

log = logging.getLogger("worker")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    session_factory = make_session_factory(make_engine(settings.database_url))
    provider = build_provider(settings.data_provider)
    strategies = default_strategies(settings)

    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())

    log.info(
        "Worker started (provider=%s, every %ss)", settings.data_provider, settings.poll_interval_seconds
    )
    while not stop.is_set():
        try:
            with session_factory() as session:
                repo = SqlRepository(session)
                result = run_once(provider, strategies, repo, {"in_app": InAppChannel(repo)})
            log.info(
                "Run complete: %d new signals, %d notifications, %d errors",
                len(result.created),
                result.notifications,
                len(result.errors),
            )
        except Exception:
            log.exception("Pipeline run failed")
        stop.wait(settings.poll_interval_seconds)
    log.info("Worker stopped")


if __name__ == "__main__":
    main()
