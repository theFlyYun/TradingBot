#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.codex.tradingbot"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
CAFFEINATE_PID_FILE="$ROOT/run/caffeinate.pid"
COMMAND_LABEL="com.codex.tradingbot.commands"
WRAPPER="/private/tmp/codex_tradingbot_scheduler.sh"
ENV_FILE="/private/tmp/codex_tradingbot_feishu.env"
CAFFEINATE_LABEL="com.codex.tradingbot.caffeinate"
CAFFEINATE_PLIST="$HOME/Library/LaunchAgents/${CAFFEINATE_LABEL}.plist"
UID_VALUE="$(id -u)"

launchctl bootout "gui/${UID_VALUE}" "$PLIST" >/dev/null 2>&1 || true
rm -f "$PLIST"
rm -f "$WRAPPER"
rm -f "$ENV_FILE"
launchctl bootout "gui/${UID_VALUE}" "$CAFFEINATE_PLIST" >/dev/null 2>&1 || true
rm -f "$CAFFEINATE_PLIST"

if [[ -f "$CAFFEINATE_PID_FILE" ]]; then
  PID="$(cat "$CAFFEINATE_PID_FILE")"
  kill "$PID" 2>/dev/null || true
  rm -f "$CAFFEINATE_PID_FILE"
fi

rm -f "$ROOT/run/scheduler.pid"
launchctl bootout "gui/${UID_VALUE}" "$HOME/Library/LaunchAgents/${COMMAND_LABEL}.plist" >/dev/null 2>&1 || true
rm -f "$HOME/Library/LaunchAgents/${COMMAND_LABEL}.plist"
echo "stopped launch agent: ${LABEL}"
