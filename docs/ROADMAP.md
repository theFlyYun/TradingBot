# Roadmap

## Near Term

- Expand the VectorBT backtest engine with parameter sweeps and benchmark comparison.
- Persist selected backtest runs as Parquet in addition to CSV reports.
- Add strategy parameter sweeps for MA/RSI thresholds.
- Add a simple report command for return, drawdown, win rate, and exposure.
- Expand LLM-assisted explanations into reusable research reports backed by local warehouse queries.
- Keep module docs split under `docs/modules/` as each area grows.

## Later

- Add multiple market data providers.
- Add portfolio-level risk and position sizing.
- Add a dashboard for watchlist, signals, and backtest results.
- Add broker integration behind a paper-trading-first boundary.
- Add more LLM providers behind `tradingbot.llm.client` without changing monitor/command code.
