# Data Warehouse Module

The local research warehouse uses DuckDB to read and write Parquet files. CSV remains fine for small human-edited lists; generated market history and analysis outputs should live in the warehouse.

## Storage Layout

```text
data/warehouse/
  prices/provider=yahoo/interval=1d/symbol=AAPL.parquet
  signals/run_date=YYYY-MM-DD/signals.parquet
```

These files are local runtime state and ignored by Git.

## Query Local Prices

```bash
python3 -m tradingbot.warehouse prices --symbols AAPL MSFT --start 2024-01-01
```

The backtesting module reads from `Warehouse.query_prices()` and does not fetch missing data during a backtest run.

## Data Freshness

Fundamental data is not tick-by-tick real time. PE, ROE, dividend yield, and market cap depend on exchange, filing, and provider updates.

Market data currently uses Yahoo-compatible daily bars configured in `config.toml`:

```toml
[market_data]
provider = "yahoo"
price_range = "1y"
interval = "1d"
request_timeout_seconds = 20
cache_ttl_seconds = 180
max_workers = 10
```
