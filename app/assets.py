"""The fixed set of assets the platform tracks."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Asset:
    symbol: str  # internal id used in subscriptions and signals
    name: str
    ticker: str  # Yahoo Finance ticker
    category: str
    base_price: float  # starting level for synthetic demo data only


ASSETS: dict[str, Asset] = {
    a.symbol: a
    for a in (
        Asset("NIFTY", "Nifty 50", "^NSEI", "index", 24000.0),
        Asset("SENSEX", "BSE Sensex", "^BSESN", "index", 80000.0),
        Asset("BANKNIFTY", "Nifty Bank", "^NSEBANK", "index", 52000.0),
        Asset("GOLD", "Gold (futures)", "GC=F", "commodity", 2600.0),
        Asset("BITCOIN", "Bitcoin (USD)", "BTC-USD", "crypto", 90000.0),
    )
}


def get_asset(symbol: str) -> Asset:
    try:
        return ASSETS[symbol.upper()]
    except KeyError:
        raise KeyError(f"Unknown asset: {symbol}") from None
