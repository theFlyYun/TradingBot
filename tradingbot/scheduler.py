from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import time

import pandas as pd

from .config import load_config
from .fundamentals import fetch_alpha_vantage_universe
from .llm import LLMError, market_observation
from .monitor import load_watchlist_symbols_and_metadata, monitor_symbols
from .notify import send_feishu_notification
from .storage import Warehouse
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


def _observation_state_path(warehouse: Warehouse) -> Path:
    return warehouse.root / "state" / "last_observations.json"


def _load_observation_state(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    if not isinstance(payload, list):
        return set()
    return {str(item) for item in payload}


def _write_observation_state(path: Path, sent_keys: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(sent_keys), ensure_ascii=False, indent=2), encoding="utf-8")


def _due_observation_keys(now: datetime, times: tuple[str, ...], sent_keys: set[str]) -> list[str]:
    due: list[str] = []
    today = now.strftime("%Y-%m-%d")
    for value in times:
        try:
            hour, minute = [int(part) for part in value.split(":", 1)]
        except ValueError:
            continue
        scheduled_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        key = f"{today} {value}"
        if scheduled_at <= now and key not in sent_keys:
            due.append(key)
    return due


def _send_market_observations(config_path: str, rows: list[dict[str, object]], due_keys: list[str]) -> None:
    if not due_keys:
        return
    config = load_config(config_path)
    try:
        report = market_observation(config, rows)
    except (LLMError, Exception) as exc:
        report = f"AI 市场观察暂不可用：{exc}"

    for key in due_keys:
        text = "\n".join(
            [
                f"{config.feishu.custom_keyword} 市场观察",
                "━━━━━━━━━━━━━━",
                "",
                f"计划时间：{key}",
                "",
                report,
            ]
        )
        try:
            send_feishu_notification(
                webhook_url=config.feishu.webhook_url,
                webhook_whitelist=config.feishu.webhook_whitelist,
                app_id=config.feishu.app_id,
                app_secret=config.feishu.app_secret,
                receive_id=config.feishu.receive_id,
                receive_id_type=config.feishu.receive_id_type,
                chat_whitelist=config.feishu.chat_whitelist,
                text=text,
            )
        except Exception as exc:
            print(f"[{_stamp()}] observation notification skipped: {exc}")


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
    last_rows: list[dict[str, object]] = []
    warehouse = Warehouse(config.runtime.warehouse_dir)
    observation_state_path = _observation_state_path(warehouse)
    sent_observations = _load_observation_state(observation_state_path)

    while True:
        now = datetime.now()
        if should_refresh_fundamentals and now >= next_fundamentals:
            _refresh_fundamentals_and_watchlist(config_path, pause_seconds)
            next_fundamentals = now + fundamentals_interval

        if now >= next_monitor:
            symbols, metadata = load_watchlist_symbols_and_metadata(config_path)
            last_rows, report_path = monitor_symbols(symbols, config_path, metadata)
            actionable = [row for row in last_rows if row.get("signal") in {"BUY", "SELL"}]
            print(f"[{_stamp()}] monitored {len(symbols)} symbols -> {report_path}; actionable={len(actionable)}")
            next_monitor = now + monitor_interval

        config = load_config(config_path)
        if config.observation.enabled and config.llm.enabled:
            due_keys = _due_observation_keys(now, config.observation.times, sent_observations)
            if due_keys:
                if not last_rows:
                    symbols, metadata = load_watchlist_symbols_and_metadata(config_path)
                    last_rows, report_path = monitor_symbols(symbols, config_path, metadata)
                    print(f"[{_stamp()}] monitored {len(symbols)} symbols for observation -> {report_path}")
                _send_market_observations(config_path, last_rows, due_keys)
                sent_observations.update(due_keys)
                _write_observation_state(observation_state_path, sent_observations)

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
