"""Command line entry points.

    python -m app.cli demo                        # zero-infrastructure end-to-end demo
    python -m app.cli init-db [--with-demo-signals]
    python -m app.cli run-once
"""

import argparse
import logging

from .config import get_settings
from .domain import DEMO_USERS
from .market_data import SyntheticProvider, build_provider
from .notify import InAppChannel
from .pipeline import Created, replay_history, run_once
from .repository import InMemoryRepository
from .strategies import default_strategies


def _print_created(created: Created) -> None:
    s = created.signal
    print(
        f"{s.bar_time.date()}  {s.asset:<10} {s.direction:<8} price={s.price:>10.2f}  "
        f"rsi={s.context.get('rsi')}  -> {created.delivered} notification(s)"
    )


def cmd_demo(_args: argparse.Namespace) -> None:
    """Replay synthetic history through the full pipeline using in-memory storage."""
    settings = get_settings()
    repo = InMemoryRepository()
    for name, assets in DEMO_USERS.items():
        user_id = repo.add_user(name)
        for asset in assets:
            repo.subscribe(user_id, asset)

    print("Replaying synthetic market history through the pipeline...\n")
    total = replay_history(
        SyntheticProvider(),
        default_strategies(settings),
        repo,
        {"in_app": InAppChannel(repo)},
        start=settings.slow_ma + 5,
        on_created=_print_created,
    )

    print(f"\n{total} signals created. Inbox per user (each user only gets what they follow):")
    for user_id, name in repo.users().items():
        inbox = repo.list_notifications(user_id, limit=1_000_000)
        received = sorted({n["asset"] for n in inbox})
        print(
            f"  {name:<6} follows {DEMO_USERS[name]} -> "
            f"{len(inbox)} notifications, received for {received}"
        )


def _open_sql():
    from .db.session import make_engine, make_session_factory

    settings = get_settings()
    engine = make_engine(settings.database_url)
    return settings, engine, make_session_factory(engine)


def cmd_init_db(args: argparse.Namespace) -> None:
    from .db.seed import seed_demo
    from .db.session import init_db
    from .db.sql_repository import SqlRepository

    settings, engine, session_factory = _open_sql()
    init_db(engine)
    with session_factory() as session:
        seed_demo(session)
        print("Schema ready, demo users seeded.")
        if args.with_demo_signals:
            repo = SqlRepository(session)
            total = replay_history(
                SyntheticProvider(),
                default_strategies(settings),
                repo,
                {"in_app": InAppChannel(repo)},
                start=settings.slow_ma + 5,
            )
            print(f"Replayed synthetic history: {total} new signals.")


def cmd_run_once(_args: argparse.Namespace) -> None:
    from .db.sql_repository import SqlRepository

    settings, _engine, session_factory = _open_sql()
    with session_factory() as session:
        repo = SqlRepository(session)
        result = run_once(
            build_provider(settings.data_provider),
            default_strategies(settings),
            repo,
            {"in_app": InAppChannel(repo)},
        )
    print(
        f"{len(result.created)} new signals, {result.notifications} notifications, "
        f"{len(result.errors)} errors"
    )
    for error in result.errors:
        print(f"  error: {error}")


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("demo", help="offline demo, no database needed").set_defaults(func=cmd_demo)

    init_parser = commands.add_parser("init-db", help="create tables and seed demo users")
    init_parser.add_argument("--with-demo-signals", action="store_true")
    init_parser.set_defaults(func=cmd_init_db)

    commands.add_parser("run-once", help="one pipeline pass against the database").set_defaults(
        func=cmd_run_once
    )

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
