from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import pandas as pd

from tradingbot.backtesting.engine import BacktestRequest, BacktestResult
from tradingbot.backtesting.vectorbt_engine import (
    BacktestDataError,
    build_backtest_signals,
    format_summary,
    load_backtest_prices,
    run_vectorbt_backtest,
    write_backtest_report,
)
from tradingbot.config import SignalConfig
from tradingbot.storage import Warehouse
from tradingbot.strategy import add_indicators


def _vectorbt_available() -> bool:
    try:
        import vectorbt  # noqa: F401
    except Exception:
        return False
    return True


def _signal_config(**overrides: object) -> SignalConfig:
    values = {
        "ma_window": 3,
        "rsi_window": 2,
        "buy_below_ma120": 0.98,
        "sell_above_ma120": 1.02,
        "buy_rsi_below": 35,
        "sell_rsi_above": 65,
        "volume_window": 2,
        "min_volume_ratio": 1.1,
        "require_volume_confirmation": False,
    }
    values.update(overrides)
    return SignalConfig(**values)


def _config(root: Path, **signal_overrides: object) -> SimpleNamespace:
    return SimpleNamespace(
        runtime=SimpleNamespace(warehouse_dir=root / "warehouse", reports_dir=root / "reports"),
        market_data=SimpleNamespace(provider="yahoo", interval="1d"),
        signals=_signal_config(**signal_overrides),
    )


def _prices(symbol: str, closes: list[float], volumes: list[int] | None = None) -> pd.DataFrame:
    start = date(2026, 1, 1)
    if volumes is None:
        volumes = [1000] * len(closes)
    return pd.DataFrame(
        {
            "symbol": [symbol] * len(closes),
            "date": [start + timedelta(days=idx) for idx in range(len(closes))],
            "open": closes,
            "high": [value * 1.01 for value in closes],
            "low": [value * 0.99 for value in closes],
            "close": closes,
            "volume": volumes,
        }
    )


class BacktestingTest(unittest.TestCase):
    def test_load_backtest_prices_uses_local_warehouse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            warehouse = Warehouse(config.runtime.warehouse_dir)
            warehouse.write_prices(_prices("AAPL", [100, 101, 102]), "yahoo", "1d", "AAPL")
            warehouse.write_prices(_prices("MSFT", [200, 201, 202]), "yahoo", "1d", "MSFT")

            result = load_backtest_prices(
                config,
                BacktestRequest(symbols=("AAPL", "MSFT"), start="2026-01-02", end="2026-01-03"),
            )

        self.assertEqual(result["symbol"].tolist(), ["AAPL", "AAPL", "MSFT", "MSFT"])
        self.assertEqual(result["date"].astype(str).min(), "2026-01-02")

    def test_load_backtest_prices_reports_missing_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            Warehouse(config.runtime.warehouse_dir).write_prices(
                _prices("AAPL", [100, 101, 102]), "yahoo", "1d", "AAPL"
            )

            with self.assertRaisesRegex(BacktestDataError, "MSFT"):
                load_backtest_prices(
                    config,
                    BacktestRequest(symbols=("AAPL", "MSFT"), start="2026-01-01", end="2026-01-03"),
                )

    def test_load_backtest_prices_reports_date_range_without_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            Warehouse(config.runtime.warehouse_dir).write_prices(
                _prices("AAPL", [100, 101, 102]), "yahoo", "1d", "AAPL"
            )

            with self.assertRaisesRegex(BacktestDataError, "历史行情为空"):
                load_backtest_prices(
                    config,
                    BacktestRequest(symbols=("AAPL",), start="2025-01-01", end="2025-01-03"),
                )

    def test_signals_shift_one_day_after_close_based_trigger(self) -> None:
        config = _config(Path("/tmp"))
        frame = _prices("AAPL", [100, 100, 100, 70, 69, 120, 125])
        enriched = add_indicators(frame, config.signals)
        close = enriched["close"].astype(float)
        raw_entry = (close < enriched["ma120"] * config.signals.buy_below_ma120) & (
            enriched["rsi"] < config.signals.buy_rsi_below
        )
        raw_exit = (close > enriched["ma120"] * config.signals.sell_above_ma120) & (
            enriched["rsi"] > config.signals.sell_rsi_above
        )

        signals = build_backtest_signals(frame, config, "ma_rsi_v1")

        expected_entries = raw_entry.shift(1).fillna(False).astype(bool).tolist()
        expected_exits = raw_exit.shift(1).fillna(False).astype(bool).tolist()
        self.assertEqual(signals.entries["AAPL"].tolist(), expected_entries)
        self.assertEqual(signals.exits["AAPL"].tolist(), expected_exits)
        self.assertFalse(bool(signals.entries["AAPL"].iloc[raw_entry.idxmax()]))

    def test_volume_strategy_filters_low_volume_triggers(self) -> None:
        config = _config(Path("/tmp"), min_volume_ratio=2.0)
        frame = _prices("AAPL", [100, 100, 100, 70, 69, 68], volumes=[1000, 1000, 1000, 1000, 1000, 1000])

        v1 = build_backtest_signals(frame, config, "ma_rsi_v1")
        v2 = build_backtest_signals(frame, config, "ma_rsi_volume_v2")

        self.assertGreater(v1.entries["AAPL"].sum(), 0)
        self.assertEqual(v2.entries["AAPL"].sum(), 0)

    def test_write_report_outputs_expected_files(self) -> None:
        request = BacktestRequest(symbols=("AAPL",), start="2026-01-01", end="2026-01-05")
        result = BacktestResult(
            request=request,
            equity_curve=pd.DataFrame({"date": ["2026-01-01"], "equity": [100000.0]}),
            trades=pd.DataFrame(
                {
                    "symbol": ["AAPL"],
                    "entry_date": ["2026-01-02"],
                    "exit_date": ["2026-01-03"],
                    "entry_price": [100.0],
                    "exit_price": [101.0],
                    "quantity": [10.0],
                    "pnl": [12.0],
                }
            ),
            metrics={
                "total_return_pct": 1.2,
                "max_drawdown_pct": -0.5,
                "sharpe_ratio": 0.8,
                "trade_count": 1,
                "win_rate_pct": 100,
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = write_backtest_report(result, Path(tmp))

            self.assertTrue((output_dir / "metrics.csv").exists())
            self.assertTrue((output_dir / "trades.csv").exists())
            self.assertTrue((output_dir / "equity_curve.csv").exists())
            summary = (output_dir / "summary.txt").read_text(encoding="utf-8")

        self.assertIn("不构成交易建议", summary)
        self.assertIn("策略：ma_rsi_v1", format_summary(result))

    @unittest.skipUnless(_vectorbt_available(), "vectorbt research extra is not importable")
    def test_run_vectorbt_backtest_returns_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(Path(tmp))
            warehouse = Warehouse(config.runtime.warehouse_dir)
            warehouse.write_prices(
                _prices("AAPL", [100, 100, 100, 70, 69, 68, 90, 120, 125, 130]), "yahoo", "1d", "AAPL"
            )

            result = run_vectorbt_backtest(
                config,
                BacktestRequest(symbols=("AAPL",), start="2026-01-01", end="2026-01-10"),
            )

        self.assertFalse(result.equity_curve.empty)
        self.assertIn("total_return_pct", result.metrics)
        self.assertIn("entry_price", result.trades.columns)


if __name__ == "__main__":
    unittest.main()
