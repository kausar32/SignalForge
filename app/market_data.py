"""Market data providers.

A provider returns a DataFrame with a DatetimeIndex and a `close` column.
"""

import zlib
from typing import Protocol

import numpy as np
import pandas as pd

from .assets import ASSETS, Asset


class MarketDataProvider(Protocol):
    def get_history(self, asset: Asset) -> pd.DataFrame: ...


class YFinanceProvider:
    """Live daily prices from Yahoo Finance (covers all five assets)."""

    def __init__(self, period: str = "1y", interval: str = "1d") -> None:
        self.period = period
        self.interval = interval

    def get_history(self, asset: Asset) -> pd.DataFrame:
        import yfinance as yf  # imported lazily so the offline demo needs no yfinance

        df = yf.Ticker(asset.ticker).history(period=self.period, interval=self.interval)
        if df.empty:
            raise RuntimeError(f"No data returned for {asset.ticker}")
        return df.rename(columns=str.lower)[["close"]].dropna()


class SyntheticProvider:
    """Deterministic random-walk prices with trend regimes.

    Used for the offline demo, tests and CI. `cursor` controls how many bars are
    visible, so history can be replayed bar by bar as if it were arriving live.
    """

    def __init__(self, total_bars: int = 300, seed: int = 7, end: str = "2026-11-13") -> None:
        self.total_bars = total_bars
        self.cursor = total_bars
        self._frames = {a.symbol: self._generate(a, seed, end) for a in ASSETS.values()}

    def _generate(self, asset: Asset, seed: int, end: str) -> pd.DataFrame:
        rng = np.random.default_rng(seed + zlib.crc32(asset.symbol.encode()))
        n = self.total_bars
        drift = np.zeros(n)
        i = 0
        while i < n:
            length = int(rng.integers(40, 81))
            drift[i : i + length] = rng.choice([-0.003, 0.0, 0.003])
            i += length
        returns = drift + rng.normal(0.0, 0.01, n)
        close = asset.base_price * np.exp(np.cumsum(returns))
        index = pd.bdate_range(end=end, periods=n)
        return pd.DataFrame({"close": close}, index=index)

    def set_cursor(self, bars: int) -> None:
        self.cursor = max(0, min(self.total_bars, bars))

    def get_history(self, asset: Asset) -> pd.DataFrame:
        return self._frames[asset.symbol].iloc[: self.cursor].copy()


def build_provider(name: str) -> MarketDataProvider:
    if name == "synthetic":
        return SyntheticProvider()
    if name == "yfinance":
        return YFinanceProvider()
    raise ValueError(f"Unknown DATA_PROVIDER '{name}' (use 'synthetic' or 'yfinance')")
