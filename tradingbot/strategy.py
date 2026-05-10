from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol

import pandas as pd

from .config import ScreeningConfig, SignalConfig
from .data import normalize_symbol


def screen_universe(universe: pd.DataFrame, config: ScreeningConfig) -> pd.DataFrame:
    frame = universe.copy()
    frame["symbol"] = frame["symbol"].map(normalize_symbol)
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
    frame["ma20"] = close.rolling(20).mean()
    frame["ma60"] = close.rolling(60).mean()
    frame["rsi"] = 100 - (100 / (1 + rs))
    frame.loc[(loss == 0) & (gain > 0), "rsi"] = 100
    frame.loc[(gain == 0) & (loss > 0), "rsi"] = 0
    frame.loc[(gain == 0) & (loss == 0), "rsi"] = 50
    frame["avg_volume"] = frame["volume"].rolling(config.volume_window).mean()
    frame["volume_ratio"] = frame["volume"] / frame["avg_volume"]
    frame["return_1d_pct"] = close.pct_change(1) * 100
    frame["return_5d_pct"] = close.pct_change(5) * 100
    frame["return_20d_pct"] = close.pct_change(20) * 100
    frame["distance_to_ma120_pct"] = (close / frame["ma120"] - 1) * 100
    frame["volatility_20d_pct"] = close.pct_change().rolling(20).std() * math.sqrt(252) * 100
    frame["high_60d"] = frame["high"].astype(float).rolling(60).max()
    frame["low_60d"] = frame["low"].astype(float).rolling(60).min()
    frame["drawdown_60d_pct"] = (close / frame["high_60d"] - 1) * 100
    range_60d = frame["high_60d"] - frame["low_60d"]
    frame["range_position_60d_pct"] = (close - frame["low_60d"]) / range_60d.replace(0, pd.NA) * 100
    frame["intraday_range_pct"] = (frame["high"].astype(float) - frame["low"].astype(float)) / close * 100
    return frame


class TradingStrategy(Protocol):
    name: str

    def add_indicators(self, prices: pd.DataFrame) -> pd.DataFrame:
        ...

    def latest_signal(self, prices: pd.DataFrame) -> dict[str, object]:
        ...


@dataclass(frozen=True)
class MaRsiStrategy:
    config: SignalConfig
    name: str = "ma_rsi"

    def add_indicators(self, prices: pd.DataFrame) -> pd.DataFrame:
        return add_indicators(prices, self.config)

    def latest_signal(self, prices: pd.DataFrame) -> dict[str, object]:
        frame = self.add_indicators(prices)
        latest = frame.dropna(subset=["ma120", "rsi"]).tail(1)
        if latest.empty:
            return {"signal": "NO_DATA", "reason": "not enough price history", "strategy": self.name}

        row = latest.iloc[0]
        close = float(row["close"])
        ma120 = float(row["ma120"])
        rsi = float(row["rsi"])
        volume_ratio = float(row["volume_ratio"]) if pd.notna(row["volume_ratio"]) else 0.0
        volume_ok = volume_ratio >= self.config.min_volume_ratio

        buy = close < ma120 * self.config.buy_below_ma120 and rsi < self.config.buy_rsi_below
        sell = close > ma120 * self.config.sell_above_ma120 and rsi > self.config.sell_rsi_above
        if self.config.require_volume_confirmation:
            buy = buy and volume_ok
            sell = sell and volume_ok

        if buy:
            signal = "BUY"
            reason = f"close < MA120*{self.config.buy_below_ma120:.2f} and RSI < {self.config.buy_rsi_below:g}"
        elif sell:
            signal = "SELL"
            reason = f"close > MA120*{self.config.sell_above_ma120:.2f} and RSI > {self.config.sell_rsi_above:g}"
        else:
            signal = "HOLD"
            reason = "no threshold crossed"

        def metric(name: str, digits: int = 2) -> float | None:
            value = row.get(name)
            if pd.isna(value):
                return None
            return round(float(value), digits)

        return {
            "symbol": row["symbol"],
            "date": str(row["date"]),
            "close": round(close, 4),
            "ma20": metric("ma20", 4),
            "ma60": metric("ma60", 4),
            "ma120": round(ma120, 4),
            "lower_band": round(ma120 * self.config.buy_below_ma120, 4),
            "upper_band": round(ma120 * self.config.sell_above_ma120, 4),
            "rsi": round(rsi, 2),
            "volume_ratio": round(volume_ratio, 2),
            "return_1d_pct": metric("return_1d_pct"),
            "return_5d_pct": metric("return_5d_pct"),
            "return_20d_pct": metric("return_20d_pct"),
            "distance_to_ma120_pct": metric("distance_to_ma120_pct"),
            "volatility_20d_pct": metric("volatility_20d_pct"),
            "drawdown_60d_pct": metric("drawdown_60d_pct"),
            "range_position_60d_pct": metric("range_position_60d_pct"),
            "intraday_range_pct": metric("intraday_range_pct"),
            "signal": signal,
            "reason": reason,
            "strategy": self.name,
        }


def build_strategy(config: SignalConfig, name: str = "ma_rsi") -> TradingStrategy:
    if name != "ma_rsi":
        raise ValueError(f"unsupported strategy: {name}")
    return MaRsiStrategy(config)


def latest_signal(prices: pd.DataFrame, config: SignalConfig) -> dict[str, object]:
    return build_strategy(config).latest_signal(prices)
