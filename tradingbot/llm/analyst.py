from __future__ import annotations

import json
from datetime import datetime
from glob import glob
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


def _compact_rows(rows: list[dict[str, object]], limit: int = 30) -> list[dict[str, object]]:
    fields = ("symbol", "name", "theme", "signal", "close", "ma120", "rsi", "volume_ratio", "reason", "data_source")
    compact: list[dict[str, object]] = []
    for row in rows[:limit]:
        compact.append({field: row.get(field) for field in fields if field in row})
    return compact


def _call(client: LLMClient | None, prompt: str) -> str:
    if client is None:
        raise LLMError("LLM is disabled")
    return client.complete(instructions=TRADING_ANALYST_INSTRUCTIONS, input_text=prompt)


def explain_signals(config: AppConfig, rows: list[dict[str, object]]) -> str:
    actionable = [row for row in rows if row.get("signal") in {"BUY", "SELL"}]
    if not actionable:
        return ""
    client = build_llm_client(config.llm)
    payload = json.dumps(_compact_rows(actionable), ensure_ascii=False, indent=2)
    return _call(client, SIGNAL_EXPLANATION_PROMPT.format(signals=payload))


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
        "latest_report": _latest_report_context(rows),
        "notes": [
            "行情数据来自项目配置的数据源和本地缓存。",
            "LLM 只负责解释和总结，不负责真实下单。",
        ],
    }
    prompt = QUESTION_PROMPT.format(
        question=question,
        context=json.dumps(context, ensure_ascii=False, indent=2),
    )
    return _call(client, prompt)


def market_observation(config: AppConfig, rows: list[dict[str, object]]) -> str:
    client = build_llm_client(config.llm)
    context = {
        "watchlist": _watchlist_context(config),
        "latest_report": _latest_report_context(rows),
    }
    prompt = OBSERVATION_PROMPT.format(context=json.dumps(context, ensure_ascii=False, indent=2))
    return _call(client, prompt)
