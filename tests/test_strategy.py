from __future__ import annotations

from datetime import date, timedelta
import unittest

import pandas as pd

from tradingbot.config import SignalConfig
from tradingbot.strategy import MaRsiStrategy, latest_signal


def _signal_config(**overrides: object) -> SignalConfig:
    values = {
        "ma_window": 3,
        "rsi_window": 2,
        "buy_below_ma120": 0.98,
        "sell_above_ma120": 1.02,
        "buy_rsi_below": 35,
        "sell_rsi_above": 65,
        "volume_window": 2,
        "min_volume_ratio": 0.8,
        "require_volume_confirmation": False,
    }
    values.update(overrides)
    return SignalConfig(**values)


def _prices(closes: list[float]) -> pd.DataFrame:
    start = date(2026, 1, 1)
    return pd.DataFrame(
        {
            "symbol": ["TEST"] * len(closes),
            "date": [start + timedelta(days=idx) for idx in range(len(closes))],
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1000] * len(closes),
        }
    )


class MaRsiStrategyTest(unittest.TestCase):
    def test_latest_signal_buy(self) -> None:
        result = MaRsiStrategy(_signal_config()).latest_signal(_prices([100, 98, 96, 94, 90]))

        self.assertEqual(result["signal"], "BUY")
        self.assertEqual(result["strategy"], "ma_rsi")
        self.assertIn("MA120", result["reason"])

    def test_latest_signal_sell(self) -> None:
        result = latest_signal(_prices([100, 102, 104, 106, 110]), _signal_config())

        self.assertEqual(result["signal"], "SELL")
        self.assertEqual(result["strategy"], "ma_rsi")

    def test_latest_signal_no_data(self) -> None:
        result = latest_signal(_prices([100, 101]), _signal_config(ma_window=5))

        self.assertEqual(result["signal"], "NO_DATA")
        self.assertEqual(result["strategy"], "ma_rsi")


if __name__ == "__main__":
    unittest.main()
