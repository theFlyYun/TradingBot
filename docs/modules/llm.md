# LLM Module

The LLM module provides a shared interface for market explanations, risk summaries, daily observations, and natural-language Q&A.

## Role in the Pipeline

```text
Market data -> Strategy calculation -> LLM explanation/risk check -> Feishu notification/Q&A
```

The model does not provide market data and does not place orders. Deterministic strategy code still owns the signal.

## Supported Providers

Current provider adapters live under `tradingbot/llm/`:

- DeepSeek Chat Completions API
- OpenAI Responses API

Configuration:

```toml
[llm]
enabled = true
provider = "deepseek"
model = "deepseek-v4-flash"
```

Local secrets belong in `.env`:

```bash
TRADINGBOT_LLM_PROVIDER="deepseek"
DEEPSEEK_API_KEY="sk-..."
DEEPSEEK_MODEL="deepseek-v4-flash"
```

## Balance Check

```bash
make balance
scripts/deepseek_balance.sh /Users/longyunfei/tradingbot-runtime/config.toml
```

## Market Observations

Beijing-time morning and evening observations can be enabled in `config.toml`:

```toml
[observation]
enabled = true
times = ["09:00", "20:30"]
```
