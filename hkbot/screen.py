from __future__ import annotations

import argparse

import pandas as pd

from .config import load_config
from .strategy import screen_universe


def main() -> int:
    parser = argparse.ArgumentParser(description="Build weekly HK stock watchlist from fundamentals.")
    parser.add_argument("--config", default="config.toml")
    args = parser.parse_args()

    config = load_config(args.config)
    universe = pd.read_csv(config.runtime.universe_csv)
    selected = screen_universe(universe, config.screening)
    config.runtime.watchlist_csv.parent.mkdir(parents=True, exist_ok=True)
    selected.to_csv(config.runtime.watchlist_csv, index=False)

    print(f"selected {len(selected)} stocks -> {config.runtime.watchlist_csv}")
    if not selected.empty:
        print(selected[["symbol", "name", "pe", "dividend_yield", "roe", "market_cap_hkd"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
