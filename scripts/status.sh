#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.codex.tradingbot"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_FILE="$ROOT/logs/scheduler.log"
CAFFEINATE_PID_FILE="$ROOT/run/caffeinate.pid"
COMMAND_LABEL="com.codex.tradingbot.commands"
CAFFEINATE_LABEL="com.codex.tradingbot.caffeinate"
UID_VALUE="$(id -u)"

if [[ -f "$PLIST" ]]; then
  echo "launch agent plist: $PLIST"
else
  echo "launch agent plist: missing"
fi

if launchctl print "gui/${UID_VALUE}/${LABEL}" >/dev/null 2>&1; then
  echo "launch agent loaded: yes"
else
  echo "launch agent loaded: no"
fi

if launchctl print "gui/${UID_VALUE}/${CAFFEINATE_LABEL}" >/dev/null 2>&1; then
  echo "caffeinate loaded: yes"
else
  echo "caffeinate loaded: no"
fi

if launchctl print "gui/${UID_VALUE}/${COMMAND_LABEL}" >/dev/null 2>&1; then
  echo "command server loaded: yes"
else
  echo "command server loaded: no"
fi

if [[ -f "$LOG_FILE" ]]; then
  echo
  echo "last log lines:"
  tail -n 30 "$LOG_FILE"
fi
