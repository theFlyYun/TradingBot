from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import time

import pandas as pd

from .config import load_config
from .fundamentals import fetch_alpha_vantage_universe
from .monitor import load_watchlist_symbols_and_metadata, monitor_symbols
from .strategy import screen_universe


def _stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _refresh_fundamentals_and_watchlist(config_path: str, pause_seconds: float) -> None:
    config = load_config(config_path)
    if config.fundamentals.provider != "alpha_vantage":
        print(f"[{_stamp()}] fundamentals refresh skipped: provider={config.fundamentals.provider}")
        return
    if not config.fundamentals.api_key:
        print(f"[{_stamp()}] fundamentals refresh skipped: ALPHAVANTAGE_API_KEY is not set")
        return

    symbols = pd.read_csv(config.runtime.symbols_csv)
    universe = fetch_alpha_vantage_universe(symbols, config.fundamentals.api_key, pause_seconds)
    universe.to_csv(config.runtime.universe_csv, index=False)

    watchlist = screen_universe(universe, config.screening)
    watchlist.to_csv(config.runtime.watchlist_csv, index=False)
    print(f"[{_stamp()}] refreshed fundamentals and selected {len(watchlist)} watchlist rows")


def run_scheduler(
    config_path: str,
    monitor_interval_minutes: float | None,
    fundamentals_interval_hours: float | None,
    refresh_fundamentals: bool | None,
    pause_seconds: float,
    run_once: bool,
) -> None:
    config = load_config(config_path)
    monitor_interval = timedelta(
        minutes=monitor_interval_minutes or config.scheduler.monitor_interval_minutes
    )
    fundamentals_interval = timedelta(
        hours=fundamentals_interval_hours or config.scheduler.fundamentals_interval_hours
    )
    should_refresh_fundamentals = (
        refresh_fundamentals if refresh_fundamentals is not None else config.scheduler.refresh_fundamentals
    )

    next_monitor = datetime.min
    next_fundamentals = datetime.min

    while True:
        now = datetime.now()
        if should_refresh_fundamentals and now >= next_fundamentals:
            _refresh_fundamentals_and_watchlist(config_path, pause_seconds)
            next_fundamentals = now + fundamentals_interval

        if now >= next_monitor:
            symbols, metadata = load_watchlist_symbols_and_metadata(config_path)
            rows, report_path = monitor_symbols(symbols, config_path, metadata)
            actionable = [row for row in rows if row.get("signal") in {"BUY", "SELL"}]
            print(f"[{_stamp()}] monitored {len(symbols)} symbols -> {report_path}; actionable={len(actionable)}")
            next_monitor = now + monitor_interval

        if run_once:
            return

        sleep_until = min(next_monitor, next_fundamentals if should_refresh_fundamentals else next_monitor)
        time.sleep(max(5, min(300, (sleep_until - datetime.now()).total_seconds())))


def main() -> int:
    parser = argparse.ArgumentParser(description="Periodically refresh data and run trading signal analysis.")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--monitor-interval-minutes", type=float)
    parser.add_argument("--fundamentals-interval-hours", type=float)
    parser.add_argument("--refresh-fundamentals", action="store_true")
    parser.add_argument("--pause-seconds", type=float, default=12.0)
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit.")
    args = parser.parse_args()

    run_scheduler(
        config_path=args.config,
        monitor_interval_minutes=args.monitor_interval_minutes,
        fundamentals_interval_hours=args.fundamentals_interval_hours,
        refresh_fundamentals=args.refresh_fundamentals,
        pause_seconds=args.pause_seconds,
        run_once=args.once,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
