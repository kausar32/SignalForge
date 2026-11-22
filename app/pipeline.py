"""The pipeline: fetch prices -> evaluate strategies -> store signals -> notify subscribers."""

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from .assets import ASSETS, Asset
from .domain import Signal
from .market_data import MarketDataProvider, SyntheticProvider
from .notify import Channel, dispatch
from .repository import Repository
from .strategies import Strategy

log = logging.getLogger(__name__)


@dataclass
class Created:
    signal: Signal
    signal_id: int
    delivered: int


@dataclass
class RunResult:
    created: list[Created] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def notifications(self) -> int:
        return sum(c.delivered for c in self.created)


def run_once(
    provider: MarketDataProvider,
    strategies: list[Strategy],
    repo: Repository,
    channels: dict[str, Channel],
    assets: Iterable[Asset] | None = None,
) -> RunResult:
    """One pass over all assets. A failure on one asset never stops the others."""
    result = RunResult()
    for asset in ASSETS.values() if assets is None else assets:
        try:
            prices = provider.get_history(asset)
        except Exception as exc:
            log.warning("Data fetch failed for %s: %s", asset.symbol, exc)
            result.errors.append(f"{asset.symbol}: {exc}")
            continue

        for strategy in strategies:
            try:
                signal = strategy.evaluate(asset, prices)
            except Exception as exc:
                log.warning("Strategy %s failed on %s: %s", strategy.name, asset.symbol, exc)
                result.errors.append(f"{asset.symbol}/{strategy.name}: {exc}")
                continue
            if signal is None:
                continue

            signal_id = repo.save_signal(signal)
            if signal_id is None:  # already stored on an earlier run
                continue
            delivered = dispatch(signal_id, signal, repo, channels)
            result.created.append(Created(signal, signal_id, delivered))
    return result


def replay_history(
    provider: SyntheticProvider,
    strategies: list[Strategy],
    repo: Repository,
    channels: dict[str, Channel],
    start: int,
    on_created: Callable[[Created], None] | None = None,
) -> int:
    """Feed synthetic history through the pipeline one bar at a time.

    Gives a realistic, repeatable stream of signals with no network or database.
    Returns the number of new signals created.
    """
    count = 0
    for cursor in range(start, provider.total_bars + 1):
        provider.set_cursor(cursor)
        for created in run_once(provider, strategies, repo, channels).created:
            count += 1
            if on_created:
                on_created(created)
    return count
