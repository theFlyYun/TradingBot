# Commands Module

The command module gives the bot a local command interface and a Feishu route through cc-connect.

## Local CLI

```bash
python3 -m tradingbot.command "tradingbot help"
python3 -m tradingbot.command "tradingbot watchlist"
```

## Local HTTP Command Server

Start:

```bash
scripts/start_command_server.sh 8787
```

Trigger:

```bash
curl -X POST http://127.0.0.1:8787/command \
  -H 'Content-Type: application/json' \
  -d '{"text":"tradingbot watchlist"}'
```

## Feishu Commands

Current cc-connect commands:

```text
/tb help
/tb watchlist
/tb alert
/tb ai 当前 watchlist 有哪些风险？
/tbhelp
/tbwatchlist
```

Supported intent groups:

- `help` / `帮助`: show command help.
- `watchlist` / `wl` / `列表`: show monitored symbols.
- `alert` / `signals` / `提醒`: refresh data, analyze signals, and send the alert card.
- `ai <question>`: ask the LLM about watchlist, signals, and project context.
