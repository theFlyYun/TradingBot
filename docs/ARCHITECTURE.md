# Architecture

The project is organized around stable boundaries so the alert demo can grow into a research and backtesting system.

## Current Runtime Flow

1. `hkbot.monitor` loads config and watchlist.
2. `hkbot.data` fetches/caches market data through a provider.
3. `hkbot.strategy` evaluates the active strategy.
4. `hkbot.storage` writes price and signal data to Parquet.
5. `hkbot.notify` sends Feishu/webhook notifications.

## Extension Areas

- `hkbot.strategies`: future strategy registry and multi-strategy composition.
- `hkbot.backtesting`: historical simulation, trades, equity curves, metrics.
- `hkbot.research`: notebooks/scripts helpers for ad hoc exploration.
- `hkbot.data`: provider adapters for Yahoo, paid market data APIs, broker APIs.
- `hkbot.storage`: DuckDB/Parquet local research warehouse.

## Data Boundary

Human-edited lists can remain CSV:

- `data/symbols.csv`
- `data/universe.csv`
- `data/watchlist.csv`

Generated history and analysis output should go to Parquet under `data/warehouse/`, which is local-only and ignored by Git.
