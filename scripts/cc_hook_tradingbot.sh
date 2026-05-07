#!/bin/zsh
set -eu

PROJECT_DIR="${TRADINGBOT_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
LOG_FILE="$PROJECT_DIR/logs/cc-connect-hooks.log"
CC_CONNECT="${CC_CONNECT_BIN:-cc-connect}"
PYTHON="${PYTHON_BIN:-python3}"

mkdir -p "$PROJECT_DIR/logs"

{
  echo "----- $(date '+%Y-%m-%d %H:%M:%S') -----"
  env | sort | grep '^CC_' || true
} >> "$LOG_FILE" 2>&1

content="${CC_HOOK_CONTENT:-}"
session_key="${CC_HOOK_SESSION_KEY:-${CC_SESSION_KEY:-}}"
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

case "$clean" in
  "/tb help"|"/tbhelp"|"tb help"|"help"|"帮助"|"h")
    reply="$(cd "$PROJECT_DIR" && "$PYTHON" -m hkbot.command tradingbot help --no-send)"
    ;;
  "/tb watchlist"|"/tbwatchlist"|"tb watchlist"|"watchlist"|"watch list"|"wl"|"列表")
    reply="$(cd "$PROJECT_DIR" && "$PYTHON" -m hkbot.command tradingbot watchlist --no-send)"
    ;;
  "/tb alert"|"/tb signals"|"tb alert"|"tb signals"|"signals"|"signal"|"alert"|"alerts"|"提醒"|"交易提醒")
    reply="已开始拉取最新行情并分析。完成后会发送交易提醒卡片。"
    (
      echo "manual alert started: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
      if cd "$PROJECT_DIR" && "$PYTHON" -m hkbot.monitor --force-notify --max-workers 10 --cache-ttl-seconds 180 >> "$LOG_FILE" 2>&1; then
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
    reply="未命中指令。可用：help / watchlist / wl / alert"
    ;;
esac

if [ -n "$session_key" ]; then
  printf '%s' "$reply" | "$CC_CONNECT" send -p tradingbot -s "$session_key" --stdin >> "$LOG_FILE" 2>&1 || true
else
  echo "missing session key, cannot reply" >> "$LOG_FILE"
fi
