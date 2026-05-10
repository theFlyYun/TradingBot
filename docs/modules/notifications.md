# Notifications Module

Notifications currently support Feishu webhook delivery and Feishu app delivery through cc-connect/self-built app flows.

## Webhook Mode

```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/..."
python3 -m tradingbot.monitor
```

If no webhook or app target is configured, the program writes local reports but does not send messages.

## App Mode

For Feishu setups without custom bots, use a self-built app route and write credentials to `.env`:

```bash
FEISHU_WEBHOOK_URL=""
FEISHU_APP_ID="cli_xxxxxxxxxxxx"
FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxx"
FEISHU_RECEIVE_ID="oc_xxxxxxxxxxxx"
FEISHU_RECEIVE_ID_TYPE="chat_id"
```

Private chats generally use `open_id`; group chats use `chat_id`.

Test delivery:

```bash
python3 -m tradingbot.test_feishu
```

## Duplicate Suppression

Scheduled alerts remember the last actionable BUY/SELL symbol set. A scheduled message is sent only when the actionable symbol set changes.

Manual `alert` commands still send the current alert immediately.

## Empty Alerts

By default, no-signal runs stay quiet. To send an explicit no-signal message each round:

```toml
[feishu]
notify_on_empty = true
```
