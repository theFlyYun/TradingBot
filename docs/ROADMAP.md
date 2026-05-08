# Roadmap

## Near Term

- Add a backtest engine that reads `Warehouse.query_prices`.
- Persist backtest runs, trades, and equity curves as Parquet.
- Add strategy parameter sweeps for MA/RSI thresholds.
- Add a simple report command for return, drawdown, win rate, and exposure.
- Expand LLM-assisted explanations into reusable research reports backed by local warehouse queries.

## Later

- Add multiple market data providers.
- Add portfolio-level risk and position sizing.
- Add a dashboard for watchlist, signals, and backtest results.
- Add broker integration behind a paper-trading-first boundary.
- Add more LLM providers behind `tradingbot.llm.client` without changing monitor/command code.
