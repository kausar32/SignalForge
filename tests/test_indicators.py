import pandas as pd

from app import indicators as ind


def test_sma_last_value():
    series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    assert ind.sma(series, 3).iloc[-1] == 4.0
    assert ind.sma(series, 3).iloc[:2].isna().all()


def test_ema_of_constant_series_is_constant():
    series = pd.Series([10.0] * 30)
    assert ind.ema(series, 5).iloc[-1] == 10.0


def test_rsi_extremes():
    rising = pd.Series([float(i) for i in range(1, 40)])
    falling = pd.Series([float(i) for i in range(40, 1, -1)])
    assert ind.rsi(rising).iloc[-1] == 100.0
    assert ind.rsi(falling).iloc[-1] == 0.0


def test_pct_change():
    series = pd.Series([100.0, 110.0])
    assert round(ind.pct_change(series).iloc[-1], 6) == 10.0
