from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

from .commands import handle_command
from .config import load_config
from .notify import send_feishu_notification


def _extract_text(payload: dict[str, object]) -> str:
    if isinstance(payload.get("text"), str):
        return str(payload["text"])

    # Basic Feishu event-shape support for later event callback integration.
    event = payload.get("event")
    if isinstance(event, dict):
        message = event.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed.get("text"), str):
                        return str(parsed["text"])
                except json.JSONDecodeError:
                    return content
    return ""


class CommandHandler(BaseHTTPRequestHandler):
    config_path = "config.toml"

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"invalid json")
            return

        # Feishu URL verification challenge.
        if isinstance(payload.get("challenge"), str):
            body = json.dumps({"challenge": payload["challenge"]}).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(body)
            return

        config = load_config(self.config_path)
        text = _extract_text(payload)
        result = handle_command(text or f"{config.feishu.custom_keyword} help", config)
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
        body = json.dumps({"ok": True, "text": result.text}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Local tradingbot command HTTP server.")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    CommandHandler.config_path = args.config
    server = HTTPServer((args.host, args.port), CommandHandler)
    print(f"command server listening on http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
