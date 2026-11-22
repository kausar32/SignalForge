import pandas as pd

from app.assets import Asset
from app.config import Settings
from app.domain import Signal
from app.market_data import SyntheticProvider
from app.notify import InAppChannel
from app.pipeline import replay_history, run_once
from app.repository import InMemoryRepository
from app.strategies import Strategy, default_strategies


class AlwaysBullish(Strategy):
    """Stub strategy: fires on every asset, every run."""

    name = "stub"

    def evaluate(self, asset: Asset, prices: pd.DataFrame) -> Signal | None:
        return Signal(asset.symbol, self.name, "BULLISH", 1.0, prices.index[-1].to_pydatetime(), {})


class FlakyProvider(SyntheticProvider):
    """Fails for one asset to prove the pipeline keeps going."""

    def get_history(self, asset: Asset) -> pd.DataFrame:
        if asset.symbol == "GOLD":
            raise RuntimeError("provider down")
        return super().get_history(asset)


def _repo() -> InMemoryRepository:
    repo = InMemoryRepository()
    alice, bob, carol = repo.add_user("alice"), repo.add_user("bob"), repo.add_user("carol")
    repo.subscribe(alice, "NIFTY")
    repo.subscribe(bob, "GOLD")
    repo.subscribe(carol, "BITCOIN", channels=("telegram",))  # no telegram handler yet
    return repo


def test_users_only_receive_what_they_follow():
    repo = _repo()
    result = run_once(SyntheticProvider(), [AlwaysBullish()], repo, {"in_app": InAppChannel(repo)})

    assert len(result.created) == 5  # one signal per asset
    assert result.notifications == 2  # alice (NIFTY) + bob (GOLD)
    assert [n["asset"] for n in repo.list_notifications(1)] == ["NIFTY"]
    assert [n["asset"] for n in repo.list_notifications(2)] == ["GOLD"]
    assert repo.list_notifications(3) == []  # carol's channel has no handler


def test_rerun_does_not_duplicate_signals_or_notifications():
    repo = _repo()
    channels = {"in_app": InAppChannel(repo)}
    provider = SyntheticProvider()
    run_once(provider, [AlwaysBullish()], repo, channels)
    second = run_once(provider, [AlwaysBullish()], repo, channels)

    assert second.created == []
    assert len(repo.list_signals(limit=100)) == 5
    assert len(repo.list_notifications(1)) == 1


def test_one_asset_failing_does_not_stop_the_run():
    repo = _repo()
    result = run_once(FlakyProvider(), [AlwaysBullish()], repo, {"in_app": InAppChannel(repo)})

    assert len(result.created) == 4
    assert len(result.errors) == 1 and "GOLD" in result.errors[0]


def test_replay_is_deterministic_and_produces_signals():
    settings = Settings("sqlite://", "synthetic", 300, 20, 50)

    def replay() -> list[str]:
        repo = InMemoryRepository()
        replay_history(
            SyntheticProvider(),
            default_strategies(settings),
            repo,
            {"in_app": InAppChannel(repo)},
            start=55,
        )
        return [
            f"{s['asset']}|{s['direction']}|{s['bar_time']}" for s in repo.list_signals(limit=1000)
        ]

    first, second = replay(), replay()
    assert len(first) > 0
    assert first == second
