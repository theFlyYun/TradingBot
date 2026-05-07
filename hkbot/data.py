from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import time
from typing import Any, Protocol

import pandas as pd
import requests

from .config import MarketDataConfig


def normalize_hk_symbol(symbol: str) -> str:
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
    def __init__(self, provider: PriceProvider, cache_dir: Path, ttl_seconds: int) -> None:
        self.provider = provider
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds

    def fetch(self, symbol: str) -> PriceFetchResult:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = _cache_path(self.cache_dir, symbol, self.provider.config.price_range, self.provider.config.interval)
        if path.exists() and time.time() - path.stat().st_mtime <= self.ttl_seconds:
            return PriceFetchResult(pd.read_pickle(path), "cache")

        frame = self.provider.fetch(symbol)
        temp_path = path.with_suffix(".tmp")
        frame.to_pickle(temp_path)
        temp_path.replace(path)
        return PriceFetchResult(frame, "live")


def build_price_provider(config: MarketDataConfig, cache_dir: Path) -> CachedPriceProvider:
    return CachedPriceProvider(
        YahooPriceProvider(config),
        cache_dir=cache_dir,
        ttl_seconds=config.cache_ttl_seconds,
    )


def fetch_daily_prices(
    symbol: str,
    range_: str = "1y",
    interval: str = "1d",
    timeout: float = 20,
) -> pd.DataFrame:
    yahoo_symbol = normalize_hk_symbol(symbol)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
    response = requests.get(
        url,
        params={"range": range_, "interval": interval, "events": "history"},
        timeout=timeout,
        headers={"User-Agent": "hk-semi-auto-trader/0.1"},
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


def _cache_path(cache_dir: Path, symbol: str, range_: str, interval: str = "1d") -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{normalize_hk_symbol(symbol)}_{range_}_{interval}")
    return cache_dir / f"{safe_name}.pkl"


def fetch_daily_prices_cached(
    symbol: str,
    cache_dir: Path,
    range_: str = "1y",
    ttl_seconds: int = 180,
) -> tuple[pd.DataFrame, bool]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(cache_dir, symbol, range_)
    if path.exists() and time.time() - path.stat().st_mtime <= ttl_seconds:
        return pd.read_pickle(path), True

    frame = fetch_daily_prices(symbol, range_)
    temp_path = path.with_suffix(".tmp")
    frame.to_pickle(temp_path)
    temp_path.replace(path)
    return frame, False


def today_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d")
