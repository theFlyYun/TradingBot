from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

import pandas as pd

from .config import AppConfig
from .llm import LLMError, answer_question


@dataclass(frozen=True)
class CommandResult:
    text: str


@dataclass(frozen=True)
class CommandSpec:
    name: str
    aliases: tuple[str, ...]
    description: str
    handler: Callable[[AppConfig, str], CommandResult] | None = None


def _normalize_command(text: str, keyword: str) -> str:
    value = text.strip()
    for prefix in ("/tb", "tb"):
        if value.lower().startswith(prefix):
            value = value[len(prefix) :].strip()
    if keyword and value.lower().startswith(keyword.lower()):
        value = value[len(keyword) :].strip()
    return value.lower()


def _strip_invocation(text: str, keyword: str) -> str:
    value = text.strip()
    for prefix in ("/tb", "tb"):
        if value.lower().startswith(prefix):
            value = value[len(prefix) :].strip()
    if keyword and value.lower().startswith(keyword.lower()):
        value = value[len(keyword) :].strip()
    return value


def command_name(text: str, keyword: str = "tradingbot") -> str | None:
    command = _normalize_command(text, keyword)
    for spec in COMMANDS:
        if command in spec.aliases or any(command.startswith(f"{alias} ") for alias in spec.aliases if alias):
            return spec.name
    return None


def command_aliases(name: str) -> tuple[str, ...]:
    for spec in COMMANDS:
        if spec.name == name:
            return spec.aliases
    return ()


def help_text(keyword: str = "tradingbot") -> str:
    command_lines: list[str] = []
    visible = [spec for spec in COMMANDS if spec.name != "unknown"]
    for idx, spec in enumerate(visible, start=1):
        aliases = " / ".join(spec.aliases[:2])
        command_lines.extend([f"{idx}. {aliases}", f"   {spec.description}", ""])

    return "\n".join(
        [
            "tradingbot 指令帮助",
            "━━━━━━━━━━━━━━",
            "",
            "发送位置",
            "飞书群里的「飞常赚智能体」",
            "",
            "可用指令",
            *command_lines,
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


def _help_command(config: AppConfig, _: str) -> CommandResult:
    return CommandResult(help_text(config.feishu.custom_keyword))


def _watchlist_command(config: AppConfig, _: str) -> CommandResult:
    return CommandResult(watchlist_text(config))


def _alert_command(_: AppConfig, __: str) -> CommandResult:
    return CommandResult("已开始拉取最新行情并分析。完成后会发送交易提醒卡片。")


def _command_body(text: str, keyword: str, aliases: tuple[str, ...]) -> str:
    command = _strip_invocation(text, keyword)
    command_lower = command.lower()
    for alias in sorted(aliases, key=len, reverse=True):
        alias_lower = alias.lower()
        if command_lower == alias_lower:
            return ""
        if alias and command_lower.startswith(f"{alias_lower} "):
            return command[len(alias) :].strip()
    return command


def _ai_command(config: AppConfig, text: str) -> CommandResult:
    question = _command_body(text, config.feishu.custom_keyword, command_aliases("ai"))
    if not question:
        return CommandResult("请在指令后写上问题，例如：/tb ai 当前 watchlist 有哪些风险？")
    if not config.llm.enabled:
        return CommandResult("AI 查询尚未启用。请在 config.toml 打开 [llm].enabled，并在 .env 配置 OPENAI_API_KEY。")
    try:
        return CommandResult(answer_question(config, question))
    except (LLMError, Exception) as exc:
        return CommandResult(f"AI 查询暂不可用：{exc}")


COMMANDS: tuple[CommandSpec, ...] = (
    CommandSpec(
        name="help",
        aliases=("help", "h", "?", ""),
        description="查看这份帮助。",
        handler=_help_command,
    ),
    CommandSpec(
        name="watchlist",
        aliases=("watchlist", "wl", "list", "watch list", "列表"),
        description="查看当前监控股票池，按主题分组。",
        handler=_watchlist_command,
    ),
    CommandSpec(
        name="alert",
        aliases=("alert", "signals", "signal", "alerts", "提醒", "交易提醒"),
        description="立即拉取行情并发送当前交易提醒。",
        handler=_alert_command,
    ),
    CommandSpec(
        name="ai",
        aliases=("ai", "ask", "问", "查询"),
        description="用自然语言向大模型查询 watchlist、信号和项目上下文。",
        handler=_ai_command,
    ),
)


def handle_command(text: str, config: AppConfig) -> CommandResult:
    command = _normalize_command(text, config.feishu.custom_keyword)
    for spec in COMMANDS:
        if spec.handler and (
            command in spec.aliases or any(command.startswith(f"{alias} ") for alias in spec.aliases if alias)
        ):
            return spec.handler(config, text)
    return CommandResult(
        "\n".join(
            [
                f"{config.feishu.custom_keyword} 未识别指令：{text}",
                "",
                "在飞书群里发送 `@飞常赚 help` 查看可用指令。",
            ]
        )
    )
