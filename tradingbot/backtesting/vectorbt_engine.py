from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from pathlib import Path
from typing import Any

import pandas as pd

from ..config import AppConfig
from ..data import normalize_symbol
from ..storage import Warehouse
from ..strategy import add_indicators
from .engine import BacktestRequest, BacktestResult


class BacktestDataError(ValueError):
    pass


class VectorBTMissingError(RuntimeError):
    pass


@dataclass(frozen=True)
class BacktestSignals:
    close: pd.DataFrame
    entries: pd.DataFrame
    exits: pd.DataFrame


def load_backtest_prices(config: AppConfig, request: BacktestRequest) -> pd.DataFrame:
    symbols = [normalize_symbol(symbol) for symbol in request.symbols]
    warehouse = Warehouse(config.runtime.warehouse_dir)
    frame = warehouse.query_prices(
        provider=config.market_data.provider,
        interval=config.market_data.interval,
        symbols=symbols,
        start=request.start,
        end=request.end,
    )
    if frame.empty:
        raise BacktestDataError("本地历史行情为空，请先运行行情刷新后再回测。")
    found = set(frame["symbol"].astype(str))
    missing = [symbol for symbol in symbols if symbol not in found]
    if missing:
        raise BacktestDataError(f"本地历史行情缺少标的：{', '.join(missing)}。请先刷新这些标的行情。")
    return frame.sort_values(["symbol", "date"]).reset_index(drop=True)


def build_backtest_signals(frame: pd.DataFrame, config: AppConfig, strategy_name: str) -> BacktestSignals:
    if strategy_name not in {"ma_rsi_v1", "ma_rsi_volume_v2"}:
        raise ValueError(f"unsupported backtest strategy: {strategy_name}")

    parts: list[pd.DataFrame] = []
    for _, group in frame.groupby("symbol", sort=False):
        enriched = add_indicators(group.sort_values("date"), config.signals)
        close = enriched["close"].astype(float)
        ma120 = enriched["ma120"].astype(float)
        rsi = enriched["rsi"].astype(float)
        volume_ratio = enriched["volume_ratio"].astype(float)
        entries = (close < ma120 * config.signals.buy_below_ma120) & (rsi < config.signals.buy_rsi_below)
        exits = (close > ma120 * config.signals.sell_above_ma120) & (rsi > config.signals.sell_rsi_above)
        if strategy_name == "ma_rsi_volume_v2":
            volume_ok = volume_ratio >= config.signals.min_volume_ratio
            entries = entries & volume_ok
            exits = exits & volume_ok
        signal_frame = enriched[["date", "symbol", "close"]].copy()
        signal_frame["entry"] = entries.shift(1).fillna(False).astype(bool)
        signal_frame["exit"] = exits.shift(1).fillna(False).astype(bool)
        parts.append(signal_frame)

    signals = pd.concat(parts, ignore_index=True)
    close_panel = _pivot(signals, "close").astype(float)
    entry_panel = _pivot(signals, "entry").reindex_like(close_panel).fillna(False).astype(bool)
    exit_panel = _pivot(signals, "exit").reindex_like(close_panel).fillna(False).astype(bool)
    return BacktestSignals(close=close_panel, entries=entry_panel, exits=exit_panel)


def run_vectorbt_backtest(config: AppConfig, request: BacktestRequest) -> BacktestResult:
    try:
        import vectorbt as vbt
    except ModuleNotFoundError as exc:
        raise VectorBTMissingError("缺少 vectorbt，请先安装研究依赖：python3 -m pip install -e '.[research]'") from exc
    except Exception as exc:
        raise VectorBTMissingError(f"vectorbt 初始化失败：{exc}") from exc

    prices = load_backtest_prices(config, request)
    signals = build_backtest_signals(prices, config, request.strategy)
    portfolio = vbt.Portfolio.from_signals(
        signals.close,
        entries=signals.entries,
        exits=signals.exits,
        init_cash=request.initial_cash,
        fees=request.fees,
        slippage=request.slippage,
        freq="1D",
    )
    equity_curve = _equity_curve(portfolio)
    trades = _trades(portfolio)
    metrics = _metrics(portfolio, trades, equity_curve)
    return BacktestResult(request=request, equity_curve=equity_curve, trades=trades, metrics=metrics)


def write_backtest_report(result: BacktestResult, reports_dir: Path) -> Path:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = reports_dir / "backtests" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([result.metrics]).to_csv(output_dir / "metrics.csv", index=False)
    result.trades.to_csv(output_dir / "trades.csv", index=False)
    result.equity_curve.to_csv(output_dir / "equity_curve.csv", index=False)
    (output_dir / "summary.txt").write_text(format_summary(result, output_dir), encoding="utf-8")
    return output_dir


def format_summary(result: BacktestResult, output_dir: Path | None = None) -> str:
    metrics = result.metrics
    lines = [
        "回测结果仅用于策略研究，不构成交易建议。",
        "",
        f"策略：{result.request.strategy}",
        f"标的：{', '.join(result.request.symbols)}",
        f"区间：{result.request.start} 至 {result.request.end}",
        f"总收益率：{metrics.get('total_return_pct', 0):.2f}%",
        f"最大回撤：{metrics.get('max_drawdown_pct', 0):.2f}%",
        f"夏普比率：{metrics.get('sharpe_ratio', 0):.2f}",
        f"交易次数：{metrics.get('trade_count', 0):.0f}",
        f"胜率：{metrics.get('win_rate_pct', 0):.2f}%",
    ]
    if output_dir is not None:
        lines.append(f"报告目录：{output_dir}")
    return "\n".join(lines)


def _pivot(frame: pd.DataFrame, value: str) -> pd.DataFrame:
    result = frame.pivot(index="date", columns="symbol", values=value).sort_index()
    result.index = pd.to_datetime(result.index)
    return result


def _equity_curve(portfolio: Any) -> pd.DataFrame:
    value = portfolio.value()
    if isinstance(value, pd.Series):
        total = value
    else:
        total = value.sum(axis=1)
    return pd.DataFrame({"date": pd.to_datetime(total.index).date, "equity": total.astype(float).to_numpy()})


def _trades(portfolio: Any) -> pd.DataFrame:
    records = portfolio.trades.records_readable
    if records is None or len(records) == 0:
        return pd.DataFrame(
            columns=["symbol", "entry_date", "exit_date", "entry_price", "exit_price", "quantity", "pnl", "return_pct"]
        )
    frame = pd.DataFrame(records).copy()
    frame = frame.rename(
        columns={
            "Column": "symbol",
            "Entry Timestamp": "entry_date",
            "Exit Timestamp": "exit_date",
            "Avg Entry Price": "entry_price",
            "Avg Exit Price": "exit_price",
            "Size": "quantity",
            "PnL": "pnl",
            "Return": "return_pct",
        }
    )
    if "return_pct" in frame.columns:
        frame["return_pct"] = pd.to_numeric(frame["return_pct"], errors="coerce") * 100
    columns = [
        "symbol",
        "entry_date",
        "exit_date",
        "entry_price",
        "exit_price",
        "quantity",
        "pnl",
        "return_pct",
        "Status",
        "Direction",
    ]
    return frame[[column for column in columns if column in frame.columns]]


def _metrics(portfolio: Any, trades: pd.DataFrame, equity_curve: pd.DataFrame) -> dict[str, float]:
    return {
        "total_return_pct": _as_float(portfolio.total_return()) * 100,
        "annual_return_pct": _as_float(portfolio.annualized_return()) * 100,
        "max_drawdown_pct": _as_float(portfolio.max_drawdown()) * 100,
        "sharpe_ratio": _as_float(portfolio.sharpe_ratio()),
        "trade_count": float(len(trades)),
        "win_rate_pct": _win_rate(trades),
        "final_equity": float(equity_curve["equity"].iloc[-1]) if not equity_curve.empty else 0.0,
    }


def _as_float(value: object) -> float:
    if isinstance(value, pd.Series):
        result = float(value.mean())
    elif isinstance(value, pd.DataFrame):
        result = float(value.mean().mean())
    else:
        result = float(value)
    return result if math.isfinite(result) else 0.0


def _win_rate(trades: pd.DataFrame) -> float:
    if trades.empty or "pnl" not in trades.columns:
        return 0.0
    pnl = pd.to_numeric(trades["pnl"], errors="coerce").dropna()
    if pnl.empty:
        return 0.0
    return float((pnl > 0).mean() * 100)
