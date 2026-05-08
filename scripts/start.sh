#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.codex.tradingbot"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_FILE="$ROOT/logs/scheduler.log"
RUN_DIR="$ROOT/run"
CAFFEINATE_PID_FILE="$RUN_DIR/caffeinate.pid"
WRAPPER="/private/tmp/codex_tradingbot_scheduler.sh"
ENV_FILE="/private/tmp/codex_tradingbot_feishu.env"
CAFFEINATE_LABEL="com.codex.tradingbot.caffeinate"
CAFFEINATE_PLIST="$HOME/Library/LaunchAgents/${CAFFEINATE_LABEL}.plist"
INTERVAL_MINUTES="${1:-30}"
INTERVAL_SECONDS="$((INTERVAL_MINUTES * 60))"
UID_VALUE="$(id -u)"
PYTHON_BIN="$(command -v python3)"

mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/logs" "$RUN_DIR"
if [[ -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env" "$ENV_FILE"
fi

cat > "$WRAPPER" <<WRAPPER
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
set -a
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"
set +a
"$PYTHON_BIN" -m tradingbot.scheduler --once >> "$LOG_FILE" 2>&1
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
  <key>StartInterval</key>
  <integer>${INTERVAL_SECONDS}</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/private/tmp/codex_tradingbot_launchd.out</string>
  <key>StandardErrorPath</key>
  <string>/private/tmp/codex_tradingbot_launchd.err</string>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/${UID_VALUE}" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/${UID_VALUE}" "$PLIST"
launchctl kickstart -k "gui/${UID_VALUE}/${LABEL}" || true

cat > "$CAFFEINATE_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${CAFFEINATE_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/caffeinate</string>
    <string>-dimsu</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/private/tmp/codex_tradingbot_caffeinate.out</string>
  <key>StandardErrorPath</key>
  <string>/private/tmp/codex_tradingbot_caffeinate.err</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/${UID_VALUE}" "$CAFFEINATE_PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/${UID_VALUE}" "$CAFFEINATE_PLIST"
launchctl kickstart -k "gui/${UID_VALUE}/${CAFFEINATE_LABEL}" || true

echo "started launch agent: ${LABEL}"
echo "interval: ${INTERVAL_MINUTES}m"
echo "plist: ${PLIST}"
echo "log: ${LOG_FILE}"
echo "caffeinate launch agent: ${CAFFEINATE_LABEL}"
