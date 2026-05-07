from __future__ import annotations

import unittest

from hkbot.backtesting import BacktestRequest, empty_result
from hkbot.research import load_prices
from hkbot.strategies import build_strategy


class ProjectLayoutTest(unittest.TestCase):
    def test_extension_packages_import(self) -> None:
        request = BacktestRequest(symbols=("AAPL",), start="2024-01-01", end="2024-12-31")
        result = empty_result(request)

        self.assertEqual(result.request.strategy, "ma_rsi")
        self.assertTrue(callable(load_prices))
        self.assertTrue(callable(build_strategy))


if __name__ == "__main__":
    unittest.main()
