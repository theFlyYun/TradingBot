# Architecture

The project is organized around stable boundaries so the alert demo can grow into a research and backtesting system.

## Current Runtime Flow

1. `tradingbot.monitor` loads config and watchlist.
2. `tradingbot.data` fetches/caches market data through a provider.
3. `tradingbot.strategy` evaluates the active strategy.
4. `tradingbot.storage` writes price and signal data to Parquet.
5. `tradingbot.notify` sends Feishu/webhook notifications.

## Extension Areas

- `tradingbot.strategies`: future strategy registry and multi-strategy composition.
- `tradingbot.backtesting`: historical simulation, trades, equity curves, metrics.
- `tradingbot.research`: notebooks/scripts helpers for ad hoc exploration.
- `tradingbot.data`: provider adapters for Yahoo, paid market data APIs, broker APIs.
- `tradingbot.storage`: DuckDB/Parquet local research warehouse.

## Data Boundary

Human-edited lists can remain CSV:

- `data/symbols.csv`
- `data/universe.csv`
- `data/watchlist.csv`

Generated history and analysis output should go to Parquet under `data/warehouse/`, which is local-only and ignored by Git.
