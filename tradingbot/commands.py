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
    return _strip_invocation(text, keyword).lower()


def _strip_invocation(text: str, keyword: str) -> str:
    value = text.strip()
    lowered = value.lower()
    for prefix in ("/tb", "tb"):
        if lowered == prefix:
            return ""
        if lowered.startswith(f"{prefix} "):
            return value[len(prefix) :].strip()
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


def info_text(config: AppConfig) -> str:
    llm_status = "已启用" if config.llm.enabled else "未启用"
    observation_status = "已启用" if config.observation.enabled else "未启用"
    observation_times = "、".join(config.observation.times) if config.observation.times else "-"
    return "\n".join(
        [
            "tradingbot 基础信息",
            "━━━━━━━━━━━━━━",
            "",
            "定位",
            "多市场半自动交易提醒和研究工具。它负责拉取行情、计算策略信号、保存本地数据、发送飞书提醒，最后由你人工确认是否操作。",
            "",
            "当前能做什么",
            "1. 维护 watchlist，按主题查看监控股票。",
            "2. 定时拉取行情并计算 MA120 / RSI 买卖观察信号。",
            "3. 有新的 BUY / SELL 股票集合变化时发送飞书提醒，避免重复播报。",
            "4. 手动触发 alert，立即刷新行情并发送交易提醒卡片。",
            "5. 将行情和信号写入 DuckDB / Parquet 本地仓库，方便后续回测。",
            "6. 通过 ai 指令调用大模型解释信号、总结风险、回答项目上下文问题。",
            "7. 预留早晚市场观察报告和后续回测、策略研究扩展。",
            "",
            "当前边界",
            "不自动下单，不保证预测结果，不把大模型当行情源。所有信号都需要人工确认。",
            "",
            "运行状态",
            f"LLM：{llm_status}",
            f"市场观察：{observation_status}（{observation_times}）",
            "",
            "常用指令",
            "help / info / watchlist / alert / ai 你的问题",
        ]
    )


def _help_command(config: AppConfig, _: str) -> CommandResult:
    return CommandResult(help_text(config.feishu.custom_keyword))


def _info_command(config: AppConfig, _: str) -> CommandResult:
    return CommandResult(info_text(config))


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
        name="info",
        aliases=("info", "about", "介绍", "基础信息"),
        description="介绍 tradingbot 是什么、能做什么和当前能力边界。",
        handler=_info_command,
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
