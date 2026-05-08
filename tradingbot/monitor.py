from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
import json
from pathlib import Path
import time

import pandas as pd

from .config import SignalConfig, load_config
from .data import CachedPriceProvider, build_price_provider, today_stamp
from .notify import build_signal_card, format_signal_message, has_actionable_signal, send_feishu_notification
from .storage import Warehouse
from .strategy import TradingStrategy, build_strategy


ACTIONABLE_SIGNALS = {"BUY", "SELL"}


def _analyze_symbol(
    symbol: str,
    provider: CachedPriceProvider,
    strategy: TradingStrategy,
    metadata: dict[str, dict[str, object]],
) -> dict[str, object]:
    started_at = time.perf_counter()
    try:
        result = provider.fetch(symbol)
        row = strategy.latest_signal(result.frame)
        row["data_source"] = result.source
    except Exception as exc:
        row = {"symbol": symbol, "signal": "ERROR", "reason": str(exc), "data_source": "error"}
    row["elapsed_ms"] = round((time.perf_counter() - started_at) * 1000)
    row.update(metadata.get(symbol, {}))
    return row


def actionable_signature(rows: list[dict[str, object]]) -> list[dict[str, str]]:
    signature = [
        {
            "symbol": str(row.get("symbol", "")),
            "signal": str(row.get("signal", "")),
            "strategy": str(row.get("strategy", "")),
        }
        for row in rows
        if row.get("signal") in ACTIONABLE_SIGNALS
    ]
    return sorted(signature, key=lambda item: (item["strategy"], item["symbol"], item["signal"]))


def _signal_state_path(warehouse: Warehouse) -> Path:
    return warehouse.root / "state" / "last_actionable_signals.json"


def _load_previous_signature(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(payload, list):
        return []
    return [
        {"symbol": str(item.get("symbol", "")), "signal": str(item.get("signal", "")), "strategy": str(item.get("strategy", ""))}
        for item in payload
        if isinstance(item, dict)
    ]


def _write_signature(path: Path, signature: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(signature, ensure_ascii=False, indent=2), encoding="utf-8")


def has_new_actionable_signal(rows: list[dict[str, object]], warehouse: Warehouse) -> bool:
    current = actionable_signature(rows)
    previous = _load_previous_signature(_signal_state_path(warehouse))
    previous_items = {(item["symbol"], item["signal"], item["strategy"]) for item in previous}
    return any((item["symbol"], item["signal"], item["strategy"]) not in previous_items for item in current)


def monitor_symbols(
    symbols: list[str],
    config_path: str = "config.toml",
    metadata: dict[str, dict[str, object]] | None = None,
    force_notify: bool = False,
    cache_ttl_seconds: int | None = None,
    max_workers: int | None = None,
) -> tuple[list[dict[str, object]], Path]:
    config = load_config(config_path)
    metadata = metadata or {}
    started_at = time.perf_counter()
    market_data_config = config.market_data
    if cache_ttl_seconds is not None:
        market_data_config = replace(market_data_config, cache_ttl_seconds=cache_ttl_seconds)
    warehouse = Warehouse(config.runtime.warehouse_dir)
    provider = build_price_provider(market_data_config, config.runtime.warehouse_dir)
    strategy = build_strategy(config.signals)
    rows_by_symbol: dict[str, dict[str, object]] = {}
    configured_workers = max_workers if max_workers is not None else market_data_config.max_workers
    worker_count = max(1, min(configured_workers, len(symbols) or 1))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(_analyze_symbol, symbol, provider, strategy, metadata): symbol
            for symbol in symbols
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                rows_by_symbol[symbol] = future.result()
            except Exception as exc:
                rows_by_symbol[symbol] = {
                    "symbol": symbol,
                    "signal": "ERROR",
                    "reason": str(exc),
                    "data_source": "error",
                }

    rows = [rows_by_symbol[symbol] for symbol in symbols]
    total_elapsed = round(time.perf_counter() - started_at, 2)
    live_count = sum(1 for row in rows if row.get("data_source") == "live")
    cache_count = sum(1 for row in rows if row.get("data_source") == "cache")

    config.runtime.reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = config.runtime.reports_dir / f"signals_{today_stamp()}.csv"
    report_frame = pd.DataFrame(rows)
    report_frame.to_csv(report_path, index=False)
    warehouse.write_signal_report(report_frame, today_stamp())

    should_notify = force_notify or has_new_actionable_signal(rows, warehouse)
    if should_notify or (config.feishu.notify_on_empty and force_notify):
        message = format_signal_message(rows, config.feishu.custom_keyword)
        refresh_summary = f"数据刷新：live {live_count} / cache {cache_count}，耗时 {total_elapsed}s"
        message = f"{message}\n\n{refresh_summary}"
        card = build_signal_card(rows, config.feishu.custom_keyword, refresh_summary) if has_actionable_signal(rows) else None
        send_feishu_notification(
            webhook_url=config.feishu.webhook_url,
            webhook_whitelist=config.feishu.webhook_whitelist,
            app_id=config.feishu.app_id,
            app_secret=config.feishu.app_secret,
            receive_id=config.feishu.receive_id,
            receive_id_type=config.feishu.receive_id_type,
            chat_whitelist=config.feishu.chat_whitelist,
            text=message,
            card=card,
        )
    _write_signature(_signal_state_path(warehouse), actionable_signature(rows))
    return rows, report_path


def load_watchlist_symbols_and_metadata(config_path: str) -> tuple[list[str], dict[str, dict[str, object]]]:
    config = load_config(config_path)
    watchlist = pd.read_csv(config.runtime.watchlist_csv)
    symbols = watchlist["symbol"].dropna().astype(str).tolist()
    metadata: dict[str, dict[str, object]] = {}
    for _, row in watchlist.iterrows():
        symbol = str(row["symbol"])
        item: dict[str, object] = {}
        for field in ("name", "theme"):
            if field in watchlist.columns and pd.notna(row.get(field)):
                item[field] = row[field]
        metadata[symbol] = item
    return symbols, metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Run daily MA120/RSI signal monitor.")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--symbols", nargs="*", help="Override watchlist symbols, e.g. 0005.HK 0939.HK")
    parser.add_argument("--force-notify", action="store_true", help="Send a notification even when there is no signal.")
    parser.add_argument("--cache-ttl-seconds", type=int, help="Override market_data.cache_ttl_seconds.")
    parser.add_argument("--max-workers", type=int, help="Override market_data.max_workers.")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.symbols:
        symbols = args.symbols
        metadata = {}
    else:
        symbols, metadata = load_watchlist_symbols_and_metadata(args.config)

    rows, report_path = monitor_symbols(
        symbols,
        args.config,
        metadata,
        force_notify=args.force_notify,
        cache_ttl_seconds=args.cache_ttl_seconds,
        max_workers=args.max_workers,
    )
    print(f"wrote {report_path}")
    print(pd.DataFrame(rows).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
