"""Backtesting package.

This package is intentionally small for now. It reserves a stable home for
historical simulations without coupling them to the live alert runtime.
"""

from .engine import BacktestRequest, BacktestResult, empty_result
from .vectorbt_engine import (
    BacktestDataError,
    VectorBTMissingError,
    format_summary,
    run_vectorbt_backtest,
    write_backtest_report,
)

__all__ = [
    "BacktestDataError",
    "BacktestRequest",
    "BacktestResult",
    "VectorBTMissingError",
    "empty_result",
    "format_summary",
    "run_vectorbt_backtest",
    "write_backtest_report",
]
