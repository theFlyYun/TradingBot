from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BacktestRequest:
    symbols: tuple[str, ...]
    start: str
    end: str
    strategy: str = "ma_rsi"
    initial_cash: float = 100_000.0


@dataclass(frozen=True)
class BacktestResult:
    request: BacktestRequest
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict[str, float]


def empty_result(request: BacktestRequest) -> BacktestResult:
    return BacktestResult(
        request=request,
        equity_curve=pd.DataFrame(columns=["date", "equity"]),
        trades=pd.DataFrame(columns=["symbol", "entry_date", "exit_date", "quantity", "pnl"]),
        metrics={},
    )
