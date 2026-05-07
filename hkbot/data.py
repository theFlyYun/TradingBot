from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import time
from typing import Any

import pandas as pd
import requests


def normalize_hk_symbol(symbol: str) -> str:
    value = symbol.strip().upper()
    if value.endswith(".HK"):
        code = value[:-3]
        if code.isdigit():
            return f"{code.zfill(4)}.HK"
    return value


def fetch_daily_prices(symbol: str, range_: str = "1y") -> pd.DataFrame:
    yahoo_symbol = normalize_hk_symbol(symbol)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
    response = requests.get(
        url,
        params={"range": range_, "interval": "1d", "events": "history"},
        timeout=20,
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


def _cache_path(cache_dir: Path, symbol: str, range_: str) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{normalize_hk_symbol(symbol)}_{range_}")
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
