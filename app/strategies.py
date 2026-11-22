"""Pluggable strategy interface plus a placeholder strategy.

To add a strategy: subclass `Strategy`, implement `evaluate`, and add it to
`default_strategies`. Nothing else in the pipeline needs to change.
"""

import math
from abc import ABC, abstractmethod

import pandas as pd

from . import indicators as ind
from .assets import Asset
from .config import Settings
from .domain import Signal


def _num(value: float) -> float | None:
    """Round for storage and turn NaN/inf into None so the value is valid JSON."""
    value = float(value)
    return None if math.isnan(value) or math.isinf(value) else round(value, 4)


class Strategy(ABC):
    name: str

    @abstractmethod
    def evaluate(self, asset: Asset, prices: pd.DataFrame) -> Signal | None:
        """Return a Signal for the latest bar, or None if nothing fired."""


class MovingAverageCrossover(Strategy):
    """Placeholder logic: fast SMA crossing the slow SMA on the latest bar.

    The real strategy is defined later; this one exists to exercise the pipeline.
    """

    name = "ma_crossover"

    def __init__(self, fast: int = 20, slow: int = 50) -> None:
        if fast >= slow:
            raise ValueError("fast period must be smaller than slow period")
        self.fast = fast
        self.slow = slow

    def evaluate(self, asset: Asset, prices: pd.DataFrame) -> Signal | None:
        close = prices["close"]
        if len(close) < self.slow + 2:
            return None

        fast_ma = ind.sma(close, self.fast)
        slow_ma = ind.sma(close, self.slow)
        prev_gap = fast_ma.iloc[-2] - slow_ma.iloc[-2]
        gap = fast_ma.iloc[-1] - slow_ma.iloc[-1]

        if prev_gap <= 0 < gap:
            direction = "BULLISH"
        elif prev_gap >= 0 > gap:
            direction = "BEARISH"
        else:
            return None

        context = {
            "fast_period": self.fast,
            "slow_period": self.slow,
            "fast_ma": _num(fast_ma.iloc[-1]),
            "slow_ma": _num(slow_ma.iloc[-1]),
            "rsi": _num(ind.rsi(close).iloc[-1]),
            "change_1d_pct": _num(ind.pct_change(close, 1).iloc[-1]),
            "change_5d_pct": _num(ind.pct_change(close, 5).iloc[-1]),
        }
        return Signal(
            asset=asset.symbol,
            strategy=self.name,
            direction=direction,
            price=float(close.iloc[-1]),
            bar_time=close.index[-1].to_pydatetime(),
            context=context,
        )


def default_strategies(settings: Settings) -> list[Strategy]:
    return [MovingAverageCrossover(settings.fast_ma, settings.slow_ma)]
