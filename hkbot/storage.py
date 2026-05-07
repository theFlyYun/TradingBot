from __future__ import annotations

from dataclasses import dataclass
from glob import glob
from pathlib import Path
import re

import duckdb
import pandas as pd


def _safe_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp.parquet")
    connection = duckdb.connect()
    try:
        connection.register("frame", frame)
        connection.execute("COPY frame TO ? (FORMAT PARQUET)", [str(temp_path)])
    finally:
        connection.close()
    temp_path.replace(path)


def read_parquet(path: Path) -> pd.DataFrame:
    connection = duckdb.connect()
    try:
        return _normalize_frame(connection.execute("SELECT * FROM read_parquet(?)", [str(path)]).df())
    finally:
        connection.close()


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in ("symbol", "provider", "interval", "strategy"):
        if column in result.columns:
            result[column] = result[column].astype(str)
    if "date" in result.columns:
        result["date"] = pd.to_datetime(result["date"]).dt.date
    return result


@dataclass(frozen=True)
class Warehouse:
    root: Path

    def price_path(self, provider: str, interval: str, symbol: str) -> Path:
        return (
            self.root
            / "prices"
            / f"provider={_safe_part(provider)}"
            / f"interval={_safe_part(interval)}"
            / f"symbol={_safe_part(symbol)}.parquet"
        )

    def signal_report_path(self, run_date: str) -> Path:
        return self.root / "signals" / f"run_date={_safe_part(run_date)}" / "signals.parquet"

    def write_prices(self, frame: pd.DataFrame, provider: str, interval: str, symbol: str) -> Path:
        path = self.price_path(provider, interval, symbol)
        frame = _normalize_frame(frame)
        if path.exists():
            existing = read_parquet(path)
            frame = (
                pd.concat([existing, frame], ignore_index=True)
                .drop_duplicates(subset=["symbol", "date"], keep="last")
                .sort_values(["symbol", "date"])
                .reset_index(drop=True)
            )
        write_parquet(frame, path)
        return path

    def read_prices(self, provider: str, interval: str, symbol: str) -> pd.DataFrame:
        return read_parquet(self.price_path(provider, interval, symbol))

    def write_signal_report(self, frame: pd.DataFrame, run_date: str) -> Path:
        path = self.signal_report_path(run_date)
        write_parquet(frame, path)
        return path

    def query_prices(
        self,
        *,
        provider: str = "yahoo",
        interval: str = "1d",
        symbols: list[str] | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        pattern = (
            self.root
            / "prices"
            / f"provider={_safe_part(provider)}"
            / f"interval={_safe_part(interval)}"
            / "*.parquet"
        )
        if not glob(str(pattern)):
            return pd.DataFrame()

        query = "SELECT * FROM read_parquet(?) WHERE 1=1"
        params: list[object] = [str(pattern)]
        if symbols:
            query += " AND symbol IN (" + ",".join(["?"] * len(symbols)) + ")"
            params.extend(symbols)
        if start:
            query += " AND date >= ?"
            params.append(start)
        if end:
            query += " AND date <= ?"
            params.append(end)
        query += " ORDER BY symbol, date"

        connection = duckdb.connect()
        try:
            return _normalize_frame(connection.execute(query, params).df())
        finally:
            connection.close()
