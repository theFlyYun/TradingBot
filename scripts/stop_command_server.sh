#!/usr/bin/env bash
set -euo pipefail

LABEL="com.codex.tradingbot.commands"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
WRAPPER="/private/tmp/codex_tradingbot_command_server.sh"
UID_VALUE="$(id -u)"

launchctl bootout "gui/${UID_VALUE}" "$PLIST" >/dev/null 2>&1 || true
rm -f "$PLIST"
rm -f "$WRAPPER"
echo "stopped command server launch agent: ${LABEL}"
