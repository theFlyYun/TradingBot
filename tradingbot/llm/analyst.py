from __future__ import annotations

import json
from datetime import date, datetime
from glob import glob
import math
from pathlib import Path

import pandas as pd

from ..config import AppConfig
from ..storage import read_parquet
from .client import LLMClient, LLMError, build_llm_client
from .prompts import (
    OBSERVATION_PROMPT,
    QUESTION_PROMPT,
    SIGNAL_EXPLANATION_PROMPT,
    TRADING_ANALYST_INSTRUCTIONS,
)


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except (TypeError, ValueError):
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _compact_rows(rows: list[dict[str, object]], limit: int = 30) -> list[dict[str, object]]:
    fields = (
        "symbol",
        "name",
        "theme",
        "date",
        "signal",
        "close",
        "ma20",
        "ma60",
        "ma120",
        "lower_band",
        "upper_band",
        "rsi",
        "volume_ratio",
        "return_1d_pct",
        "return_5d_pct",
        "return_20d_pct",
        "distance_to_ma120_pct",
        "volatility_20d_pct",
        "drawdown_60d_pct",
        "range_position_60d_pct",
        "intraday_range_pct",
        "reason",
        "data_source",
    )
    compact: list[dict[str, object]] = []
    for row in rows[:limit]:
        compact.append({field: row.get(field) for field in fields if field in row})
    return compact


def _signal_brief_rows(rows: list[dict[str, object]], limit: int = 8) -> list[dict[str, object]]:
    fields = (
        "symbol",
        "name",
        "theme",
        "signal",
        "close",
        "ma20",
        "ma60",
        "ma120",
        "rsi",
        "volume_ratio",
        "return_5d_pct",
        "return_20d_pct",
        "distance_to_ma120_pct",
        "volatility_20d_pct",
        "drawdown_60d_pct",
        "range_position_60d_pct",
    )
    return [{field: row.get(field) for field in fields if field in row} for row in rows[:limit]]


def _market_reaction_context(rows: list[dict[str, object]]) -> dict[str, object]:
    valid_rows = [row for row in rows if row.get("signal") not in {"ERROR", "NO_DATA"}]
    actionable = [row for row in valid_rows if row.get("signal") in {"BUY", "SELL"}]
    by_signal = {
        signal: sum(1 for row in valid_rows if row.get("signal") == signal)
        for signal in ("BUY", "SELL", "HOLD")
    }
    by_theme: dict[str, dict[str, int]] = {}
    for row in actionable:
        theme = str(row.get("theme") or "未分组")
        signal = str(row.get("signal"))
        by_theme.setdefault(theme, {"BUY": 0, "SELL": 0})
        by_theme[theme][signal] += 1

    def sort_key(row: dict[str, object], field: str) -> float:
        try:
            return abs(float(row.get(field) or 0))
        except (TypeError, ValueError):
            return 0.0

    return {
        "total_symbols": len(rows),
        "valid_symbols": len(valid_rows),
        "error_symbols": len(rows) - len(valid_rows),
        "signal_counts": by_signal,
        "actionable_by_theme": by_theme,
        "largest_5d_reactions": _compact_rows(
            sorted(valid_rows, key=lambda row: sort_key(row, "return_5d_pct"), reverse=True),
            limit=8,
        ),
        "highest_volume_reactions": _compact_rows(
            sorted(valid_rows, key=lambda row: sort_key(row, "volume_ratio"), reverse=True),
            limit=8,
        ),
    }


def _signal_quality_context(rows: list[dict[str, object]]) -> dict[str, object]:
    valid_rows = [row for row in rows if row.get("signal") not in {"ERROR", "NO_DATA"}]
    actionable = [row for row in valid_rows if row.get("signal") in {"BUY", "SELL"}]
    by_signal = {
        signal: sum(1 for row in actionable if row.get("signal") == signal)
        for signal in ("BUY", "SELL")
    }
    by_theme: dict[str, dict[str, int]] = {}
    for row in actionable:
        theme = str(row.get("theme") or "未分组")
        signal = str(row.get("signal"))
        by_theme.setdefault(theme, {"BUY": 0, "SELL": 0})
        by_theme[theme][signal] += 1

    def value(row: dict[str, object], field: str) -> float:
        try:
            return float(row.get(field) or 0)
        except (TypeError, ValueError):
            return 0.0

    priority = sorted(
        actionable,
        key=lambda row: (
            abs(value(row, "return_5d_pct")),
            abs(value(row, "distance_to_ma120_pct")),
            abs(value(row, "volume_ratio")),
        ),
        reverse=True,
    )
    return {
        "signal_counts": by_signal,
        "actionable_by_theme": by_theme,
        "priority_signals": _signal_brief_rows(priority, limit=6),
        "data_quality": {
            "valid_symbols": len(valid_rows),
            "error_symbols": len(rows) - len(valid_rows),
        },
    }


def _call(client: LLMClient | None, prompt: str) -> str:
    if client is None:
        raise LLMError("LLM is disabled")
    return client.complete(instructions=TRADING_ANALYST_INSTRUCTIONS, input_text=prompt)


def _clean_signal_analysis(text: str) -> str:
    replacements = {
        "BUX": "买入观察",
        "BUY": "买入观察",
        "SELL": "卖出观察",
    }
    cleaned = text
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    return cleaned


def _clean_ai_answer(text: str) -> str:
    cleaned = _clean_signal_analysis(text)
    for phrase in ("建议买入", "建议卖出", "建议等回调", "建议等待回调"):
        cleaned = cleaned.replace(phrase, "需要继续核验")
    cleaned = cleaned.replace("等待回调至", "观察是否回落至")
    return cleaned


def explain_signals(config: AppConfig, rows: list[dict[str, object]]) -> str:
    actionable = [row for row in rows if row.get("signal") in {"BUY", "SELL"}]
    if not actionable:
        return ""
    client = build_llm_client(config.llm)
    context = {
        "strategy_boundary": "代码信号只由 MA120 阈值和 RSI 阈值触发；以下数据仅用于二次解读和风控分层。",
        "market": _signal_quality_context(rows),
    }
    payload = json.dumps(context, ensure_ascii=False, indent=2)
    return _clean_signal_analysis(_call(client, SIGNAL_EXPLANATION_PROMPT.format(context=payload)))


def _watchlist_context(config: AppConfig, limit: int = 80) -> list[dict[str, object]]:
    frame = pd.read_csv(config.runtime.watchlist_csv)
    fields = [column for column in ("symbol", "name", "theme") if column in frame.columns]
    return frame[fields].head(limit).to_dict("records")


def _latest_report_context(rows: list[dict[str, object]] | None = None) -> dict[str, object]:
    rows = rows or []
    actionable = [row for row in rows if row.get("signal") in {"BUY", "SELL"}]
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "actionable_count": len(actionable),
        "signals": _compact_rows(actionable or rows, limit=40),
        "market_reaction": _market_reaction_context(rows),
    }


def _question_report_context(rows: list[dict[str, object]] | None = None) -> dict[str, object]:
    rows = rows or []
    valid_rows = [row for row in rows if row.get("signal") not in {"ERROR", "NO_DATA"}]
    actionable = [row for row in valid_rows if row.get("signal") in {"BUY", "SELL"}]
    holds = [row for row in valid_rows if row.get("signal") == "HOLD"]

    def value(row: dict[str, object], field: str) -> float:
        try:
            return float(row.get(field) or 0)
        except (TypeError, ValueError):
            return 0.0

    hold_candidates = sorted(
        holds,
        key=lambda row: (
            value(row, "return_20d_pct"),
            value(row, "distance_to_ma120_pct"),
            -abs(value(row, "rsi") - 55),
        ),
        reverse=True,
    )
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "signal_quality": _signal_quality_context(rows),
        "hold_trend_candidates": _signal_brief_rows(hold_candidates, limit=8),
    }


def _load_latest_signal_rows(config: AppConfig) -> list[dict[str, object]]:
    pattern = str(config.runtime.warehouse_dir / "signals" / "run_date=*" / "signals.parquet")
    paths = sorted(glob(pattern))
    if not paths:
        return []
    try:
        frame = read_parquet(Path(paths[-1]))
    except Exception:
        return []
    return frame.to_dict("records")


def answer_question(config: AppConfig, question: str, rows: list[dict[str, object]] | None = None) -> str:
    client = build_llm_client(config.llm)
    rows = rows or _load_latest_signal_rows(config)
    context = {
        "watchlist": _watchlist_context(config),
        "latest_report": _question_report_context(rows),
        "notes": [
            "行情数据来自项目配置的数据源和本地缓存。",
            "LLM 只负责解释和总结，不负责真实下单。",
        ],
    }
    prompt = QUESTION_PROMPT.format(
        question=question,
        context=json.dumps(_json_safe(context), ensure_ascii=False, indent=2),
    )
    return _clean_ai_answer(_call(client, prompt))


def market_observation(config: AppConfig, rows: list[dict[str, object]]) -> str:
    client = build_llm_client(config.llm)
    context = {
        "watchlist": _watchlist_context(config),
        "latest_report": _latest_report_context(rows),
    }
    prompt = OBSERVATION_PROMPT.format(context=json.dumps(_json_safe(context), ensure_ascii=False, indent=2))
    return _call(client, prompt)
