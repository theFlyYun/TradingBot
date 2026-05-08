from __future__ import annotations

import argparse

from .config import load_config
from .notify import send_feishu_notification


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a Feishu test message using current config/env.")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--text", default="半自动交易监控：飞书通知测试成功。")
    args = parser.parse_args()

    config = load_config(args.config)
    send_feishu_notification(
        webhook_url=config.feishu.webhook_url,
        webhook_whitelist=config.feishu.webhook_whitelist,
        app_id=config.feishu.app_id,
        app_secret=config.feishu.app_secret,
        receive_id=config.feishu.receive_id,
        receive_id_type=config.feishu.receive_id_type,
        chat_whitelist=config.feishu.chat_whitelist,
        text=f"{config.feishu.custom_keyword} {args.text}".strip(),
    )
    print("sent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
