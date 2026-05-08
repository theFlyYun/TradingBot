from __future__ import annotations

import json

import requests


def _num(value: object, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def _signal_color(signal: object) -> str:
    if signal == "BUY":
        return "green"
    if signal == "SELL":
        return "red"
    return "grey"


def _trigger_text(row: dict[str, object]) -> str:
    signal = row.get("signal")
    if signal == "BUY":
        return "价 < MA120*0.88，RSI < 30"
    if signal == "SELL":
        return "价 > MA120*1.12，RSI > 70"
    return str(row.get("reason", ""))


def format_signal_message(signals: list[dict[str, object]], custom_keyword: str = "tradingbot") -> str:
    actionable = [row for row in signals if row.get("signal") in {"BUY", "SELL"}]
    prefix = f"{custom_keyword} " if custom_keyword else ""
    if not actionable:
        return f"{prefix}半自动交易监控：本轮无买入/卖出信号。"

    buys = [row for row in actionable if row.get("signal") == "BUY"]
    sells = [row for row in actionable if row.get("signal") == "SELL"]
    lines = [
        f"{prefix}交易提醒",
        "",
        f"买入观察 {len(buys)} | 卖出观察 {len(sells)}",
        "",
        "请人工确认后再下单。",
    ]
    for title, rows in (("买入观察", buys), ("卖出观察", sells)):
        if not rows:
            continue
        lines.append("")
        lines.append(f"【{title}】")
        for row in rows:
            name = f" {row['name']}" if row.get("name") else ""
            theme = f"｜{row['theme']}" if row.get("theme") else ""
            lines.append(
                f"{row.get('symbol')}{name}{theme}\n"
                f"  价 {_num(row.get('close'))}｜MA120 {_num(row.get('ma120'))}｜RSI {_num(row.get('rsi'))}\n"
                f"  触发：{_trigger_text(row)}"
            )
            lines.append("")
    return "\n".join(lines).strip()


def build_signal_card(
    signals: list[dict[str, object]],
    custom_keyword: str = "tradingbot",
    refresh_summary: str = "",
) -> dict[str, object]:
    actionable = [row for row in signals if row.get("signal") in {"BUY", "SELL"}]
    buys = [row for row in actionable if row.get("signal") == "BUY"]
    sells = [row for row in actionable if row.get("signal") == "SELL"]
    template = "red" if sells else "green"
    elements: list[dict[str, object]] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**买入观察 {len(buys)} ｜ 卖出观察 {len(sells)}**\n\n请人工确认后再下单。",
            },
        },
    ]

    for title, rows in (("买入观察", buys), ("卖出观察", sells)):
        if not rows:
            continue
        elements.append({"tag": "hr"})
        elements.append(
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**{title}**"},
            }
        )
        for row in rows:
            name = f" {row['name']}" if row.get("name") else ""
            theme = f"｜{row['theme']}" if row.get("theme") else ""
            color = _signal_color(row.get("signal"))
            title_text = f"<font color='{color}'>**{row.get('symbol')}{name}**</font>{theme}"
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"{title_text}\n\n"
                            f"价格：**{_num(row.get('close'))}** ｜ MA120：{_num(row.get('ma120'))} ｜ RSI：{_num(row.get('rsi'))}\n\n"
                            f"触发：{_trigger_text(row)}"
                        ),
                    },
                }
            )

    if refresh_summary:
        elements.append({"tag": "hr"})
        elements.append(
            {
                "tag": "note",
                "elements": [{"tag": "plain_text", "content": refresh_summary}],
            }
        )

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": template,
            "title": {"tag": "plain_text", "content": f"{custom_keyword} 交易提醒"},
        },
        "elements": elements,
    }


def has_actionable_signal(signals: list[dict[str, object]]) -> bool:
    return any(row.get("signal") in {"BUY", "SELL"} for row in signals)


def _get_tenant_access_token(app_id: str, app_secret: str) -> str:
    response = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"Feishu token error: {payload}")
    return str(payload["tenant_access_token"])


def send_feishu_app_message(
    app_id: str,
    app_secret: str,
    receive_id: str,
    receive_id_type: str,
    text: str,
) -> None:
    if not (app_id and app_secret and receive_id):
        return
    token = _get_tenant_access_token(app_id, app_secret)
    response = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages",
        params={"receive_id_type": receive_id_type},
        headers={"Authorization": f"Bearer {token}"},
        json={
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        },
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"Feishu message error: {payload}")


def send_feishu_app_card(
    app_id: str,
    app_secret: str,
    receive_id: str,
    receive_id_type: str,
    card: dict[str, object],
) -> None:
    if not (app_id and app_secret and receive_id):
        return
    token = _get_tenant_access_token(app_id, app_secret)
    response = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages",
        params={"receive_id_type": receive_id_type},
        headers={"Authorization": f"Bearer {token}"},
        json={
            "receive_id": receive_id,
            "msg_type": "interactive",
            "content": json.dumps(card, ensure_ascii=False),
        },
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"Feishu card message error: {payload}")


def send_feishu(webhook_url: str, text: str) -> None:
    if not webhook_url:
        return
    response = requests.post(
        webhook_url,
        json={"msg_type": "text", "content": {"text": text}},
        timeout=15,
    )
    response.raise_for_status()


def send_feishu_card(webhook_url: str, card: dict[str, object]) -> None:
    if not webhook_url:
        return
    response = requests.post(
        webhook_url,
        json={"msg_type": "interactive", "card": card},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code", 0) != 0:
        raise RuntimeError(f"Feishu card error: {payload}")


def send_feishu_notification(
    *,
    webhook_url: str,
    webhook_whitelist: tuple[str, ...] = (),
    app_id: str,
    app_secret: str,
    receive_id: str,
    receive_id_type: str,
    chat_whitelist: tuple[str, ...] = (),
    text: str,
    card: dict[str, object] | None = None,
) -> None:
    webhook_targets = tuple(dict.fromkeys(value for value in (*webhook_whitelist, webhook_url) if value))
    sent = False

    for chat_id in chat_whitelist:
        if card:
            send_feishu_app_card(app_id, app_secret, chat_id, "chat_id", card)
        else:
            send_feishu_app_message(app_id, app_secret, chat_id, "chat_id", text)
        sent = True

    for target in webhook_targets:
        if card:
            try:
                send_feishu_card(target, card)
                sent = True
                continue
            except Exception:
                pass
        send_feishu(target, text)
        sent = True

    if sent:
        return

    if not (app_id and app_secret and receive_id):
        raise ValueError(
            "Feishu is not configured. Set FEISHU_WEBHOOK_URL, or set "
            "FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_RECEIVE_ID and FEISHU_RECEIVE_ID_TYPE, "
            "or configure feishu.chat_whitelist / feishu.webhook_whitelist."
        )
    if card:
        send_feishu_app_card(app_id, app_secret, receive_id, receive_id_type, card)
    else:
        send_feishu_app_message(app_id, app_secret, receive_id, receive_id_type, text)
