#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.codex.tradingbot.commands"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_FILE="$ROOT/logs/command_server.log"
PORT="${1:-8787}"
UID_VALUE="$(id -u)"
PYTHON_BIN="$(command -v python3)"
WRAPPER="/private/tmp/codex_tradingbot_command_server.sh"

mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/logs" "$ROOT/run"

cat > "$WRAPPER" <<WRAPPER
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
exec "$PYTHON_BIN" -u -m tradingbot.command_server --port "$PORT"
WRAPPER
chmod +x "$WRAPPER"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${WRAPPER}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG_FILE}</string>
  <key>StandardErrorPath</key>
  <string>${LOG_FILE}</string>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/${UID_VALUE}" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/${UID_VALUE}" "$PLIST"
launchctl kickstart -k "gui/${UID_VALUE}/${LABEL}" || true

echo "started command server launch agent: ${LABEL}"
echo "url: http://127.0.0.1:${PORT}"
echo "plist: ${PLIST}"
echo "log: ${LOG_FILE}"
