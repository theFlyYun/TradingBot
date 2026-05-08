"""Backtesting package.

This package is intentionally small for now. It reserves a stable home for
historical simulations without coupling them to the live alert runtime.
"""

from .engine import BacktestRequest, BacktestResult, empty_result

__all__ = ["BacktestRequest", "BacktestResult", "empty_result"]
