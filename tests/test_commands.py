from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import pandas as pd

from tradingbot.commands import command_name, handle_command


def _config(watchlist_csv: Path, keyword: str = "tradingbot") -> SimpleNamespace:
    return SimpleNamespace(
        feishu=SimpleNamespace(custom_keyword=keyword),
        runtime=SimpleNamespace(watchlist_csv=watchlist_csv),
        llm=SimpleNamespace(enabled=False),
        observation=SimpleNamespace(enabled=False, times=("09:00", "20:30")),
    )


class CommandRoutingTest(unittest.TestCase):
    def test_command_aliases_route_to_canonical_names(self) -> None:
        self.assertEqual(command_name("/tb help"), "help")
        self.assertEqual(command_name("info"), "info")
        self.assertEqual(command_name("tradingbot about"), "info")
        self.assertEqual(command_name("tb watchlist"), "watchlist")
        self.assertEqual(command_name("tradingbot wl"), "watchlist")
        self.assertEqual(command_name("signals"), "alert")
        self.assertEqual(command_name("交易提醒"), "alert")
        self.assertEqual(command_name("/tb ai 当前 watchlist 有哪些风险？"), "ai")
        self.assertEqual(command_name("tb ai 当前 watchlist 有哪些风险？"), "ai")
        self.assertIsNone(command_name("tbai 当前 watchlist 有哪些风险？"))
        self.assertIsNone(command_name("nonsense"))

    def test_unknown_command_is_short_and_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchlist.csv"
            pd.DataFrame([{"symbol": "AAPL", "name": "Apple", "theme": "Tech"}]).to_csv(path, index=False)
            result = handle_command("unknown", _config(path))

        self.assertIn("未识别指令", result.text)
        self.assertIn("help", result.text)

    def test_watchlist_command_groups_by_theme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchlist.csv"
            pd.DataFrame(
                [
                    {"symbol": "AAPL", "name": "Apple", "theme": "Tech"},
                    {"symbol": "MSFT", "name": "Microsoft", "theme": "Tech"},
                    {"symbol": "NEE", "name": "NextEra", "theme": "Power"},
                ]
            ).to_csv(path, index=False)
            result = handle_command("wl", _config(path))

        self.assertIn("监控数量：3", result.text)
        self.assertIn("【Tech】2", result.text)
        self.assertIn("AAPL Apple", result.text)

    def test_info_command_describes_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchlist.csv"
            pd.DataFrame([{"symbol": "AAPL", "name": "Apple", "theme": "Tech"}]).to_csv(path, index=False)
            result = handle_command("info", _config(path))

        self.assertIn("tradingbot 基础信息", result.text)
        self.assertIn("当前能做什么", result.text)
        self.assertIn("不自动下单", result.text)

    def test_ai_command_reports_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "watchlist.csv"
            pd.DataFrame([{"symbol": "AAPL", "name": "Apple", "theme": "Tech"}]).to_csv(path, index=False)
            result = handle_command("/tb ai 当前 watchlist 有哪些风险？", _config(path))

        self.assertIn("AI 查询尚未启用", result.text)


if __name__ == "__main__":
    unittest.main()
