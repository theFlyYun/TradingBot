from __future__ import annotations

from dataclasses import dataclass
import math
import time

import pandas as pd
import requests


@dataclass(frozen=True)
class FundamentalRow:
    symbol: str
    name: str
    pe: float
    dividend_yield: float
    roe: float
    market_cap_hkd: float


def _to_float(value: object) -> float:
    if value in (None, "", "None", "N/A", "-"):
        return math.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def fetch_alpha_vantage_overview(symbol: str, api_key: str, session: requests.Session | None = None) -> dict[str, object]:
    client = session or requests.Session()
    response = client.get(
        "https://www.alphavantage.co/query",
        params={"function": "OVERVIEW", "symbol": symbol, "apikey": api_key},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload or "Note" in payload or "Information" in payload or "Error Message" in payload:
        raise ValueError(f"Alpha Vantage did not return overview for {symbol}: {payload}")
    return payload


def alpha_vantage_to_row(symbol: str, fallback_name: str, payload: dict[str, object]) -> FundamentalRow:
    pe = _to_float(payload.get("PERatio"))
    dividend_yield = _to_float(payload.get("DividendYield"))
    roe = _to_float(payload.get("ReturnOnEquityTTM"))
    market_cap = _to_float(payload.get("MarketCapitalization"))
    currency = str(payload.get("Currency") or "").upper()

    # Hong Kong tickers usually return HKD from Alpha Vantage. Keep the field
    # explicit because the screening threshold is denominated in HKD.
    market_cap_hkd = market_cap if currency in {"", "HKD"} else market_cap
    return FundamentalRow(
        symbol=symbol,
        name=str(payload.get("Name") or fallback_name),
        pe=pe,
        dividend_yield=dividend_yield,
        roe=roe,
        market_cap_hkd=market_cap_hkd,
    )


def fetch_alpha_vantage_universe(symbols: pd.DataFrame, api_key: str, pause_seconds: float = 12.0) -> pd.DataFrame:
    if not api_key:
        raise ValueError("ALPHAVANTAGE_API_KEY is required for live fundamentals")

    session = requests.Session()
    rows: list[FundamentalRow] = []
    for index, item in symbols.reset_index(drop=True).iterrows():
        symbol = str(item["symbol"])
        fallback_name = str(item.get("name", symbol))
        payload = fetch_alpha_vantage_overview(symbol, api_key, session=session)
        rows.append(alpha_vantage_to_row(symbol, fallback_name, payload))
        if index < len(symbols) - 1:
            time.sleep(pause_seconds)

    return pd.DataFrame([row.__dict__ for row in rows])
