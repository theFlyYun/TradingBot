from __future__ import annotations

import argparse

from .config import load_config
from .storage import Warehouse


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the local DuckDB/Parquet warehouse.")
    parser.add_argument("--config", default="config.toml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prices = subparsers.add_parser("prices", help="Query stored price history.")
    prices.add_argument("--symbols", nargs="*", help="Symbols to query, e.g. AAPL 0700.HK")
    prices.add_argument("--start", help="Inclusive start date, YYYY-MM-DD.")
    prices.add_argument("--end", help="Inclusive end date, YYYY-MM-DD.")
    prices.add_argument("--provider", default="yahoo")
    prices.add_argument("--interval", default="1d")
    prices.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    config = load_config(args.config)
    warehouse = Warehouse(config.runtime.warehouse_dir)

    if args.command == "prices":
        frame = warehouse.query_prices(
            provider=args.provider,
            interval=args.interval,
            symbols=args.symbols,
            start=args.start,
            end=args.end,
        )
        if args.limit:
            frame = frame.tail(args.limit)
        print(frame.to_string(index=False))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
