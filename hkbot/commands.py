from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from .config import AppConfig


@dataclass(frozen=True)
class CommandResult:
    text: str


def _normalize_command(text: str, keyword: str) -> str:
    value = text.strip()
    if keyword and value.lower().startswith(keyword.lower()):
        value = value[len(keyword) :].strip()
    return value.lower()


def help_text(keyword: str = "tradingbot") -> str:
    return "\n".join(
        [
            "tradingbot 指令帮助",
            "━━━━━━━━━━━━━━",
            "",
            "发送位置",
            "飞书群里的「飞常赚智能体」",
            "",
            "可用指令",
            "1. help",
            "   查看这份帮助。",
            "",
            "2. watchlist / wl",
            "   查看当前监控股票池，按主题分组。",
            "",
            "3. signals / alert",
            "   立即拉取行情并发送当前交易提醒。",
            "",
            "注意",
            "旧的 tradingbot webhook 机器人只负责自动行情提醒，不接收交互指令。",
        ]
    )


def watchlist_text(config: AppConfig) -> str:
    frame = pd.read_csv(config.runtime.watchlist_csv)
    lines = [
        "tradingbot 当前 Watchlist",
        "━━━━━━━━━━━━━━",
        "",
        f"监控数量：{len(frame)}",
        f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    if "theme" not in frame.columns:
        items = [f"{idx}. {symbol}" for idx, symbol in enumerate(frame["symbol"].astype(str).tolist(), start=1)]
        return "\n".join(lines + [""] + items)

    for theme, group in frame.groupby("theme", dropna=False):
        lines.append("")
        lines.append(f"【{theme}】{len(group)}")
        for idx, (_, row) in enumerate(group.iterrows(), start=1):
            name = f" {row['name']}" if pd.notna(row.get("name")) else ""
            lines.append(f"{idx}. {row['symbol']}{name}")
    return "\n".join(lines)


def handle_command(text: str, config: AppConfig) -> CommandResult:
    command = _normalize_command(text, config.feishu.custom_keyword)
    if command in {"help", "h", "?", ""}:
        return CommandResult(help_text(config.feishu.custom_keyword))
    if command in {"watchlist", "wl", "list"}:
        return CommandResult(watchlist_text(config))
    return CommandResult(
        "\n".join(
            [
                f"{config.feishu.custom_keyword} 未识别指令：{text}",
                "",
                "在飞书群里发送 `@飞常赚 help` 查看可用指令。",
            ]
        )
    )
