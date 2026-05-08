from __future__ import annotations

import argparse

import pandas as pd

from .config import load_config
from .fundamentals import fetch_alpha_vantage_universe


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh latest available fundamentals into data/universe.csv.")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--provider", choices=("alpha_vantage",), default="alpha_vantage")
    parser.add_argument("--pause-seconds", type=float, default=12.0, help="Pause between API calls to respect free limits.")
    args = parser.parse_args()

    config = load_config(args.config)
    symbols = pd.read_csv(config.runtime.symbols_csv)

    try:
        if args.provider == "alpha_vantage":
            universe = fetch_alpha_vantage_universe(symbols, config.fundamentals.api_key, args.pause_seconds)
        else:
            raise ValueError(f"unsupported provider: {args.provider}")
    except ValueError as exc:
        parser.error(str(exc))

    config.runtime.universe_csv.parent.mkdir(parents=True, exist_ok=True)
    universe.to_csv(config.runtime.universe_csv, index=False)
    print(f"refreshed {len(universe)} rows -> {config.runtime.universe_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
