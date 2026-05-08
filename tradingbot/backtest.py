from __future__ import annotations

import argparse

from .config import load_config
from .data import fetch_daily_prices
from .strategy import build_strategy


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview historical threshold crossings for one symbol.")
    parser.add_argument("symbol")
    parser.add_argument("--config", default="config.toml")
    args = parser.parse_args()

    config = load_config(args.config)
    strategy = build_strategy(config.signals)
    frame = strategy.add_indicators(fetch_daily_prices(args.symbol, range_="2y")).dropna(subset=["ma120", "rsi"])
    frame["buy"] = (frame["close"] < frame["ma120"] * config.signals.buy_below_ma120) & (
        frame["rsi"] < config.signals.buy_rsi_below
    )
    frame["sell"] = (frame["close"] > frame["ma120"] * config.signals.sell_above_ma120) & (
        frame["rsi"] > config.signals.sell_rsi_above
    )
    hits = frame.loc[frame["buy"] | frame["sell"], ["date", "symbol", "close", "ma120", "rsi", "buy", "sell"]]
    if hits.empty:
        print("no historical threshold crossings in the selected range")
    else:
        print(hits.tail(30).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
