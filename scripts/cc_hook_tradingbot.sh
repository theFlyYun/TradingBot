#!/bin/zsh
set -eu

PROJECT_DIR="${TRADINGBOT_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
LOG_FILE="$PROJECT_DIR/logs/cc-connect-hooks.log"
STATE_FILE="$PROJECT_DIR/run/cc-hook-processed.tsv"
CC_CONNECT="${CC_CONNECT_BIN:-cc-connect}"
PYTHON="${PYTHON_BIN:-python3}"

mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/run"

{
  echo "----- $(date '+%Y-%m-%d %H:%M:%S') -----"
  env | sort | grep '^CC_' || true
} >> "$LOG_FILE" 2>&1

content="${CC_HOOK_CONTENT:-}"
session_key="${CC_HOOK_SESSION_KEY:-${CC_SESSION_KEY:-}}"
hook_timestamp="${CC_HOOK_TIMESTAMP:-}"
allowed_chats="${TRADINGBOT_ALLOWED_CHATS:-}"

chat_id=""
if [ -n "$session_key" ]; then
  chat_id="$(printf '%s' "$session_key" | awk -F: '{print $2}')"
fi

if [ -n "$allowed_chats" ] && [ -n "$chat_id" ] && ! printf ',%s,' "$allowed_chats" | grep -q ",$chat_id,"; then
  echo "ignored unauthorized chat: $chat_id" >> "$LOG_FILE"
  exit 0
fi

clean="$(printf '%s' "$content" \
  | sed -E 's#<at id="[^"]+">[^<]*</at>##g; s#<at id=[^>]+></at>##g; s#^@[^[:space:]]+[[:space:]]*##g' \
  | xargs)"

if [ -n "$hook_timestamp" ]; then
  event_epoch="$(date -j -f "%Y-%m-%dT%H:%M:%S%z" "$(printf '%s' "$hook_timestamp" | sed -E 's/([+-][0-9]{2}):([0-9]{2})$/\1\2/')" "+%s" 2>/dev/null || true)"
  now_epoch="$(date "+%s")"
  if [ -n "$event_epoch" ] && [ $((now_epoch - event_epoch)) -gt 120 ]; then
    echo "ignored stale message: timestamp=$hook_timestamp clean=$clean" >> "$LOG_FILE"
    exit 0
  fi
fi

fingerprint="$(printf '%s\t%s\t%s\n' "$session_key" "$hook_timestamp" "$clean" | shasum -a 256 | awk '{print $1}')"
if [ -s "$STATE_FILE" ] && grep -q "^$fingerprint	" "$STATE_FILE"; then
  echo "ignored duplicate message: fingerprint=$fingerprint clean=$clean" >> "$LOG_FILE"
  exit 0
fi
printf '%s\t%s\t%s\n' "$fingerprint" "$(date '+%Y-%m-%d %H:%M:%S')" "$clean" >> "$STATE_FILE"
tail -200 "$STATE_FILE" > "$STATE_FILE.tmp"
mv "$STATE_FILE.tmp" "$STATE_FILE"

command_name="$(cd "$PROJECT_DIR" && "$PYTHON" -m tradingbot.command "$clean" --match)"

case "$command_name" in
  "help"|"watchlist")
    reply="$(cd "$PROJECT_DIR" && "$PYTHON" -m tradingbot.command "$clean" --no-send)"
    ;;
  "ai")
    reply=""
    (
      echo "ai command started: $(date '+%Y-%m-%d %H:%M:%S') clean=$clean" >> "$LOG_FILE"
      if final_reply="$(cd "$PROJECT_DIR" && "$PYTHON" -m tradingbot.command "$clean" --no-send 2>> "$LOG_FILE")"; then
        :
      else
        final_reply="AI 查询暂不可用，请稍后再试。"
      fi
      if [ -n "$session_key" ] && [ -n "$final_reply" ]; then
        printf '%s' "$final_reply" | "$CC_CONNECT" send -p tradingbot -s "$session_key" --stdin >> "$LOG_FILE" 2>&1 || true
      fi
      echo "ai command finished: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
    ) &
    ;;
  "alert")
    reply="$(cd "$PROJECT_DIR" && "$PYTHON" -m tradingbot.command "$clean" --no-send)"
    (
      echo "manual alert started: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
      if cd "$PROJECT_DIR" && "$PYTHON" -m tradingbot.monitor --force-notify --max-workers 10 --cache-ttl-seconds 180 >> "$LOG_FILE" 2>&1; then
        final_reply=""
      else
        final_reply="当前交易提醒触发失败，请查看后台日志。"
      fi
      if [ -n "$session_key" ] && [ -n "$final_reply" ]; then
        printf '%s' "$final_reply" | "$CC_CONNECT" send -p tradingbot -s "$session_key" --stdin >> "$LOG_FILE" 2>&1 || true
      fi
      echo "manual alert finished: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
    ) &
    ;;
  *)
    reply="$(cd "$PROJECT_DIR" && "$PYTHON" -m tradingbot.command "$clean" --no-send)"
    ;;
esac

if [ -n "$session_key" ] && [ -n "$reply" ]; then
  printf '%s' "$reply" | "$CC_CONNECT" send -p tradingbot -s "$session_key" --stdin >> "$LOG_FILE" 2>&1 || true
elif [ -z "$session_key" ]; then
  echo "missing session key, cannot reply" >> "$LOG_FILE"
fi
