# Strategy Module

The current strategy is intentionally deterministic. It generates observations for a human to review; it does not place real orders.

## Screening Rules

The watchlist starts from a basic universe filter:

- PE `< 20`
- Dividend yield `> 4%`
- ROE `> 10%`
- Market cap above the configured threshold

Input files:

- `data/symbols.csv`: symbols to refresh fundamentals for.
- `data/universe.csv`: basic stock universe and fundamental data.
- `data/watchlist.csv`: filtered monitored list.

## Signal Rules

The live alert strategy uses close price, MA120, and RSI:

- BUY observation: close `< MA120 * 0.88` and RSI `< 30`
- SELL observation: close `> MA120 * 1.12` and RSI `> 70`
- Volume confirmation can be enabled in `config.toml`.

The implementation lives in:

- `tradingbot/strategy.py`: current MA/RSI logic and compatibility entry points.
- `tradingbot/strategies/`: future strategy registry and composition modules.

## Current Boundary

Strategies produce deterministic `BUY` / `SELL` / `HOLD` signals. LLM output may explain, summarize, or risk-check the result, but it is not the source of the signal.
