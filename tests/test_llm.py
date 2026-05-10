from __future__ import annotations

from datetime import date
import json
import unittest

from tradingbot.llm.analyst import _clean_ai_answer, _clean_signal_analysis, _compact_rows, _json_safe, _market_reaction_context
from tradingbot.llm.balance import format_deepseek_balance, parse_deepseek_balance
from tradingbot.llm.client import _chat_finish_reason, _extract_chat_text, _extract_response_text


class LLMClientTest(unittest.TestCase):
    def test_extracts_output_text_shortcut(self) -> None:
        self.assertEqual(_extract_response_text({"output_text": "hello"}), "hello")

    def test_extracts_nested_response_text(self) -> None:
        payload = {
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": "hello"},
                        {"type": "output_text", "text": "world"},
                    ]
                }
            ]
        }

        self.assertEqual(_extract_response_text(payload), "hello\nworld")

    def test_extracts_chat_completion_text(self) -> None:
        payload = {"choices": [{"message": {"content": "deepseek ok"}}]}

        self.assertEqual(_extract_chat_text(payload), "deepseek ok")

    def test_extracts_chat_finish_reason(self) -> None:
        payload = {"choices": [{"message": {"content": ""}, "finish_reason": "length"}]}

        self.assertEqual(_chat_finish_reason(payload), " (finish_reason=length)")

    def test_compact_rows_includes_trader_context_fields(self) -> None:
        rows = [
            {
                "symbol": "AAPL",
                "signal": "BUY",
                "ma20": 190,
                "ma60": 185,
                "ma120": 180,
                "return_5d_pct": -6.5,
                "volatility_20d_pct": 28.1,
                "drawdown_60d_pct": -12.4,
                "range_position_60d_pct": 18.2,
            }
        ]

        compact = _compact_rows(rows)

        self.assertEqual(compact[0]["ma20"], 190)
        self.assertEqual(compact[0]["return_5d_pct"], -6.5)
        self.assertEqual(compact[0]["range_position_60d_pct"], 18.2)

    def test_market_reaction_context_groups_actionable_themes(self) -> None:
        rows = [
            {"symbol": "AAPL", "theme": "AI", "signal": "BUY", "return_5d_pct": -5, "volume_ratio": 1.2},
            {"symbol": "MSFT", "theme": "AI", "signal": "SELL", "return_5d_pct": 8, "volume_ratio": 2.0},
            {"symbol": "TSLA", "theme": "EV", "signal": "HOLD", "return_5d_pct": 2, "volume_ratio": 0.9},
        ]

        context = _market_reaction_context(rows)

        self.assertEqual(context["signal_counts"]["BUY"], 1)
        self.assertEqual(context["signal_counts"]["SELL"], 1)
        self.assertEqual(context["actionable_by_theme"]["AI"]["BUY"], 1)
        self.assertEqual(context["actionable_by_theme"]["AI"]["SELL"], 1)

    def test_clean_signal_analysis_uses_chinese_signal_labels(self) -> None:
        text = "BUX 集中在 Game，AAPL — BUY，MSFT — SELL"

        cleaned = _clean_signal_analysis(text)

        self.assertEqual(cleaned, "买入观察 集中在 Game，AAPL — 买入观察，MSFT — 卖出观察")

    def test_clean_ai_answer_softens_trading_advice_language(self) -> None:
        text = "AAPL BUY，MSFT SELL，建议等回调。等待回调至MA20。"

        cleaned = _clean_ai_answer(text)

        self.assertEqual(cleaned, "AAPL 买入观察，MSFT 卖出观察，需要继续核验。观察是否回落至MA20。")

    def test_formats_deepseek_balance_without_key_material(self) -> None:
        balance = parse_deepseek_balance(
            {
                "is_available": True,
                "balance_infos": [
                    {
                        "currency": "CNY",
                        "total_balance": "19.93",
                        "granted_balance": "0.00",
                        "topped_up_balance": "19.93",
                    }
                ],
            }
        )

        text = format_deepseek_balance(balance)

        self.assertIn("DeepSeek API 可用：true", text)
        self.assertIn("总余额：19.93", text)
        self.assertNotIn("sk-", text)

    def test_json_safe_converts_dates_and_nan_values(self) -> None:
        payload = _json_safe({"date": date(2026, 5, 10), "value": float("nan")})

        self.assertEqual(payload, {"date": "2026-05-10", "value": None})
        json.dumps(payload)


if __name__ == "__main__":
    unittest.main()
