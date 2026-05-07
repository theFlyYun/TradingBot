from __future__ import annotations

import pandas as pd

from .config import ScreeningConfig, SignalConfig
from .data import normalize_hk_symbol


def screen_universe(universe: pd.DataFrame, config: ScreeningConfig) -> pd.DataFrame:
    frame = universe.copy()
    frame["symbol"] = frame["symbol"].map(normalize_hk_symbol)
    mask = (
        (frame["pe"] < config.max_pe)
        & (frame["dividend_yield"] > config.min_dividend_yield)
        & (frame["roe"] > config.min_roe)
        & (frame["market_cap_hkd"] > config.min_market_cap_hkd)
    )
    selected = frame.loc[mask].sort_values(["roe", "dividend_yield"], ascending=False)
    return selected.reset_index(drop=True)


def add_indicators(prices: pd.DataFrame, config: SignalConfig) -> pd.DataFrame:
    frame = prices.copy()
    close = frame["close"].astype(float)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(config.rsi_window).mean()
    loss = (-delta.clip(upper=0)).rolling(config.rsi_window).mean()
    rs = gain / loss.replace(0, pd.NA)

    frame["ma120"] = close.rolling(config.ma_window).mean()
    frame["rsi"] = 100 - (100 / (1 + rs))
    frame["avg_volume"] = frame["volume"].rolling(config.volume_window).mean()
    frame["volume_ratio"] = frame["volume"] / frame["avg_volume"]
    return frame


def latest_signal(prices: pd.DataFrame, config: SignalConfig) -> dict[str, object]:
    frame = add_indicators(prices, config)
    latest = frame.dropna(subset=["ma120", "rsi"]).tail(1)
    if latest.empty:
        return {"signal": "NO_DATA", "reason": "not enough price history"}

    row = latest.iloc[0]
    close = float(row["close"])
    ma120 = float(row["ma120"])
    rsi = float(row["rsi"])
    volume_ratio = float(row["volume_ratio"]) if pd.notna(row["volume_ratio"]) else 0.0
    volume_ok = volume_ratio >= config.min_volume_ratio

    buy = close < ma120 * config.buy_below_ma120 and rsi < config.buy_rsi_below
    sell = close > ma120 * config.sell_above_ma120 and rsi > config.sell_rsi_above
    if config.require_volume_confirmation:
        buy = buy and volume_ok
        sell = sell and volume_ok

    if buy:
        signal = "BUY"
        reason = f"close < MA120*{config.buy_below_ma120:.2f} and RSI < {config.buy_rsi_below:g}"
    elif sell:
        signal = "SELL"
        reason = f"close > MA120*{config.sell_above_ma120:.2f} and RSI > {config.sell_rsi_above:g}"
    else:
        signal = "HOLD"
        reason = "no threshold crossed"

    return {
        "symbol": row["symbol"],
        "date": str(row["date"]),
        "close": round(close, 4),
        "ma120": round(ma120, 4),
        "lower_band": round(ma120 * config.buy_below_ma120, 4),
        "upper_band": round(ma120 * config.sell_above_ma120, 4),
        "rsi": round(rsi, 2),
        "volume_ratio": round(volume_ratio, 2),
        "signal": signal,
        "reason": reason,
    }
