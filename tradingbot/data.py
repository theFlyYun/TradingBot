from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import time
from typing import Any, Protocol

import pandas as pd
import requests

from .config import MarketDataConfig
from .storage import Warehouse


def normalize_symbol(symbol: str) -> str:
    value = symbol.strip().upper()
    if value.endswith(".HK"):
        code = value[:-3]
        if code.isdigit():
            return f"{code.zfill(4)}.HK"
    return value



@dataclass(frozen=True)
class PriceFetchResult:
    frame: pd.DataFrame
    source: str


class PriceProvider(Protocol):
    config: MarketDataConfig

    def fetch(self, symbol: str) -> pd.DataFrame:
        ...


class YahooPriceProvider:
    def __init__(self, config: MarketDataConfig) -> None:
        if config.provider != "yahoo":
            raise ValueError(f"unsupported market data provider: {config.provider}")
        self.config = config

    def fetch(self, symbol: str) -> pd.DataFrame:
        return fetch_daily_prices(
            symbol,
            range_=self.config.price_range,
            interval=self.config.interval,
            timeout=self.config.request_timeout_seconds,
        )


class CachedPriceProvider:
    def __init__(self, provider: PriceProvider, warehouse: Warehouse, ttl_seconds: int) -> None:
        self.provider = provider
        self.warehouse = warehouse
        self.ttl_seconds = ttl_seconds

    def fetch(self, symbol: str) -> PriceFetchResult:
        yahoo_symbol = normalize_symbol(symbol)
        path = self.warehouse.price_path(self.provider.config.provider, self.provider.config.interval, yahoo_symbol)
        if path.exists() and time.time() - path.stat().st_mtime <= self.ttl_seconds:
            return PriceFetchResult(self.warehouse.read_prices(self.provider.config.provider, self.provider.config.interval, yahoo_symbol), "cache")

        frame = self.provider.fetch(symbol)
        self.warehouse.write_prices(frame, self.provider.config.provider, self.provider.config.interval, yahoo_symbol)
        return PriceFetchResult(frame, "live")


def build_price_provider(config: MarketDataConfig, warehouse_dir: Path) -> CachedPriceProvider:
    return CachedPriceProvider(
        YahooPriceProvider(config),
        warehouse=Warehouse(warehouse_dir),
        ttl_seconds=config.cache_ttl_seconds,
    )


def fetch_daily_prices(
    symbol: str,
    range_: str = "1y",
    interval: str = "1d",
    timeout: float = 20,
) -> pd.DataFrame:
    yahoo_symbol = normalize_symbol(symbol)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
    response = requests.get(
        url,
        params={"range": range_, "interval": interval, "events": "history"},
        timeout=timeout,
        headers={"User-Agent": "tradingbot/0.1"},
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    result = payload.get("chart", {}).get("result") or []
    if not result:
        error = payload.get("chart", {}).get("error")
        raise ValueError(f"Yahoo returned no data for {yahoo_symbol}: {error}")

    item = result[0]
    timestamps = item.get("timestamp") or []
    quote = (item.get("indicators", {}).get("quote") or [{}])[0]
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(timestamps, unit="s").date,
            "open": quote.get("open", []),
            "high": quote.get("high", []),
            "low": quote.get("low", []),
            "close": quote.get("close", []),
            "volume": quote.get("volume", []),
        }
    )
    frame = frame.dropna(subset=["close"]).reset_index(drop=True)
    frame.insert(0, "symbol", yahoo_symbol)
    return frame


def fetch_daily_prices_cached(
    symbol: str,
    cache_dir: Path,
    range_: str = "1y",
    ttl_seconds: int = 180,
) -> tuple[pd.DataFrame, bool]:
    warehouse = Warehouse(cache_dir)
    yahoo_symbol = normalize_symbol(symbol)
    path = warehouse.price_path("yahoo", "1d", yahoo_symbol)
    if path.exists() and time.time() - path.stat().st_mtime <= ttl_seconds:
        return warehouse.read_prices("yahoo", "1d", yahoo_symbol), True

    frame = fetch_daily_prices(symbol, range_)
    warehouse.write_prices(frame, "yahoo", "1d", yahoo_symbol)
    return frame, False


def today_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d")
