# Backtesting Module

The first backtesting version is for strategy validation, not full trading simulation. It uses open-source VectorBT and local DuckDB/Parquet historical prices.

## Install Research Dependencies

```bash
python3 -m pip install -e ".[research]"
```

## Run a Backtest

```bash
python3 -m tradingbot.backtesting.run \
  --symbols AAPL MSFT \
  --start 2024-01-01 \
  --end 2026-05-10 \
  --strategy ma_rsi_v1
```

Installed command:

```bash
tradingbot-backtest --symbols AAPL --start 2024-01-01 --end 2026-05-10
```

Runtime-copy example:

```bash
tradingbot-backtest \
  --config /Users/longyunfei/tradingbot-runtime/config.toml \
  --symbols AAPL \
  --start 2024-01-01 \
  --end 2026-05-10
```

## Supported Strategies

- `ma_rsi_v1`: current MA120 + RSI observation rules.
- `ma_rsi_volume_v2`: v1 plus volume-ratio filtering.

## Defaults

- Long-only.
- No short selling.
- Initial cash: `100000`.
- Fees: `0.1%`.
- Slippage: `0.05%`.
- Signals generated from close data are shifted by 1 daily bar before execution to avoid same-close lookahead bias.

## Outputs

Reports are written to `reports/backtests/<run_id>/`:

```text
metrics.csv       # return, annual return, drawdown, Sharpe, trade count, win rate
trades.csv        # symbol, entry/exit date, entry/exit price, quantity, PnL
equity_curve.csv  # date, equity
summary.txt       # short Chinese summary suitable for Feishu
```

## Caveats

Backtest results are for research only and are not trading advice. Current Yahoo daily data may differ by adjusted prices, time zones, and market calendars. v1 aims to validate strategy direction quickly, not provide institution-grade execution simulation.
