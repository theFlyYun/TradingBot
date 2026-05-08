# Architecture

The project is organized around stable boundaries so the alert demo can grow into a research and backtesting system.

## Current Runtime Flow

1. `tradingbot.monitor` loads config and watchlist.
2. `tradingbot.data` fetches/caches market data through a provider.
3. `tradingbot.strategy` evaluates the active strategy.
4. `tradingbot.llm` optionally explains actionable signals and risk checks them.
5. `tradingbot.storage` writes price and signal data to Parquet.
6. `tradingbot.notify` sends Feishu/webhook notifications.

## Extension Areas

- `tradingbot.strategies`: future strategy registry and multi-strategy composition.
- `tradingbot.backtesting`: historical simulation, trades, equity curves, metrics.
- `tradingbot.research`: notebooks/scripts helpers for ad hoc exploration.
- `tradingbot.data`: provider adapters for Yahoo, paid market data APIs, broker APIs.
- `tradingbot.llm`: model-provider boundary for DeepSeek/OpenAI now and other LLM providers later.
- `tradingbot.storage`: DuckDB/Parquet local research warehouse.

## LLM Boundary

LLM usage is intentionally isolated under `tradingbot.llm`:

- `client.py` owns provider/API calls, currently DeepSeek Chat Completions and OpenAI Responses.
- `prompts.py` owns prompt templates.
- `analyst.py` owns trading-specific explanation, market observation, and Q&A helpers.

Strategies still produce deterministic `BUY` / `SELL` / `HOLD` signals in code. The model may explain or summarize those signals, but it should not be the source of market data or an automatic order decision.

## Data Boundary

Human-edited lists can remain CSV:

- `data/symbols.csv`
- `data/universe.csv`
- `data/watchlist.csv`

Generated history and analysis output should go to Parquet under `data/warehouse/`, which is local-only and ignored by Git.
