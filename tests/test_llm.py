from __future__ import annotations

import unittest

from tradingbot.llm.client import _extract_chat_text, _extract_response_text


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


if __name__ == "__main__":
    unittest.main()
