from __future__ import annotations

import argparse

from .commands import command_name, handle_command
from .config import load_config
from .notify import send_feishu_notification


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a tradingbot command and send the response to Feishu.")
    parser.add_argument("text", nargs="*", help="Command text, e.g. tradingbot help")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--match", action="store_true", help="Print the canonical command name and exit.")
    parser.add_argument("--no-send", action="store_true", help="Print only; do not send to Feishu.")
    args = parser.parse_args()

    config = load_config(args.config)
    text = " ".join(args.text) if args.text else f"{config.feishu.custom_keyword} help"
    if args.match:
        print(command_name(text, config.feishu.custom_keyword) or "unknown")
        return 0

    result = handle_command(text, config)
    print(result.text)

    if not args.no_send:
        send_feishu_notification(
            webhook_url=config.feishu.webhook_url,
            webhook_whitelist=config.feishu.webhook_whitelist,
            app_id=config.feishu.app_id,
            app_secret=config.feishu.app_secret,
            receive_id=config.feishu.receive_id,
            receive_id_type=config.feishu.receive_id_type,
            chat_whitelist=config.feishu.chat_whitelist,
            text=result.text,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
