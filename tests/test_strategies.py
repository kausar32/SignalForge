import pandas as pd
import pytest

from app.assets import get_asset
from app.strategies import MovingAverageCrossover

NIFTY = get_asset("NIFTY")


def _frame(prices: list[float]) -> pd.DataFrame:
    index = pd.bdate_range(end="2026-11-13", periods=len(prices))
    return pd.DataFrame({"close": prices}, index=index)


def _first_signal(start: list[float], step: float, max_bars: int = 40):
    """Keep extending a trend one bar at a time until the strategy fires."""
    strategy = MovingAverageCrossover(fast=3, slow=5)
    prices = list(start)
    for _ in range(max_bars):
        prices.append(prices[-1] + step)
        signal = strategy.evaluate(NIFTY, _frame(prices))
        if signal:
            return signal, prices
    return None, prices


def test_bullish_cross_fires_on_first_bar_only():
    signal, prices = _first_signal([100 - i for i in range(15)], step=+5)
    assert signal is not None
    assert signal.direction == "BULLISH"
    assert signal.asset == "NIFTY"
    assert signal.price == prices[-1]
    # One more bar in the same direction must NOT fire again (cross already happened).
    assert MovingAverageCrossover(3, 5).evaluate(NIFTY, _frame(prices + [prices[-1] + 5])) is None


def test_bearish_cross():
    signal, _ = _first_signal([100 + i for i in range(15)], step=-5)
    assert signal is not None
    assert signal.direction == "BEARISH"


def test_no_signal_on_flat_prices():
    assert MovingAverageCrossover(3, 5).evaluate(NIFTY, _frame([100.0] * 30)) is None


def test_not_enough_data_returns_none():
    assert MovingAverageCrossover(3, 5).evaluate(NIFTY, _frame([1.0, 2.0, 3.0])) is None


def test_context_is_json_safe_and_complete():
    signal, _ = _first_signal([100 - i for i in range(30)], step=+5)
    assert signal is not None
    for key in ("fast_ma", "slow_ma", "rsi", "change_1d_pct", "change_5d_pct"):
        assert key in signal.context
    for value in signal.context.values():
        assert value is None or isinstance(value, (int, float))


def test_invalid_periods_rejected():
    with pytest.raises(ValueError):
        MovingAverageCrossover(fast=50, slow=20)


def test_dedupe_key_is_stable():
    first, prices = _first_signal([100 - i for i in range(15)], step=+5)
    again = MovingAverageCrossover(3, 5).evaluate(NIFTY, _frame(prices))
    assert first is not None and again is not None
    assert first.dedupe_key == again.dedupe_key
