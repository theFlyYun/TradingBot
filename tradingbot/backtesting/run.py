from __future__ import annotations

import argparse

from ..config import load_config
from .engine import BacktestRequest
from .vectorbt_engine import (
    BacktestDataError,
    VectorBTMissingError,
    format_summary,
    run_vectorbt_backtest,
    write_backtest_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a VectorBT strategy validation backtest from local warehouse data."
    )
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--symbols", nargs="+", required=True, help="Symbols to backtest, e.g. AAPL MSFT 0700.HK")
    parser.add_argument("--start", required=True, help="Inclusive start date, YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="Inclusive end date, YYYY-MM-DD")
    parser.add_argument("--strategy", default="ma_rsi_v1", choices=("ma_rsi_v1", "ma_rsi_volume_v2"))
    parser.add_argument("--initial-cash", type=float, default=100_000.0)
    parser.add_argument("--fees", type=float, default=0.001, help="Fee ratio, default 0.001 = 0.1%%")
    parser.add_argument("--slippage", type=float, default=0.0005, help="Slippage ratio, default 0.0005 = 0.05%%")
    args = parser.parse_args()

    config = load_config(args.config)
    request = BacktestRequest(
        symbols=tuple(args.symbols),
        start=args.start,
        end=args.end,
        strategy=args.strategy,
        initial_cash=args.initial_cash,
        fees=args.fees,
        slippage=args.slippage,
    )
    try:
        result = run_vectorbt_backtest(config, request)
    except (BacktestDataError, VectorBTMissingError, ValueError) as exc:
        print(f"回测失败：{exc}")
        return 1
    output_dir = write_backtest_report(result, config.runtime.reports_dir)
    print(format_summary(result, output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
