from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tradingbot.monitor import _signal_state_path, _write_signature, actionable_signature, has_new_actionable_signal
from tradingbot.storage import Warehouse


class MonitorNotificationStateTest(unittest.TestCase):
    def test_actionable_signature_ignores_hold_and_sorts(self) -> None:
        rows = [
            {"symbol": "MSFT", "signal": "SELL", "strategy": "ma_rsi"},
            {"symbol": "AAPL", "signal": "HOLD", "strategy": "ma_rsi"},
            {"symbol": "AAPL", "signal": "BUY", "strategy": "ma_rsi"},
        ]

        self.assertEqual(
            actionable_signature(rows),
            [
                {"symbol": "AAPL", "signal": "BUY", "strategy": "ma_rsi"},
                {"symbol": "MSFT", "signal": "SELL", "strategy": "ma_rsi"},
            ],
        )

    def test_repeated_actionable_signal_is_not_new(self) -> None:
        rows = [{"symbol": "AAPL", "signal": "BUY", "strategy": "ma_rsi"}]
        with tempfile.TemporaryDirectory() as tmp:
            warehouse = Warehouse(Path(tmp))
            self.assertTrue(has_new_actionable_signal(rows, warehouse))

            _write_signature(_signal_state_path(warehouse), actionable_signature(rows))

            self.assertFalse(has_new_actionable_signal(rows, warehouse))

    def test_changed_actionable_signal_is_new(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            warehouse = Warehouse(Path(tmp))
            _write_signature(
                _signal_state_path(warehouse),
                [{"symbol": "AAPL", "signal": "BUY", "strategy": "ma_rsi"}],
            )

            rows = [{"symbol": "AAPL", "signal": "SELL", "strategy": "ma_rsi"}]

            self.assertTrue(has_new_actionable_signal(rows, warehouse))


if __name__ == "__main__":
    unittest.main()
