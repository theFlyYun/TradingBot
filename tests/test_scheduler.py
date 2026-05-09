from __future__ import annotations

from datetime import datetime
import unittest

from tradingbot.scheduler import _due_observation_keys


class SchedulerObservationTest(unittest.TestCase):
    def test_observation_due_after_scheduled_time_until_sent(self) -> None:
        now = datetime(2026, 5, 9, 12, 30)

        self.assertEqual(_due_observation_keys(now, ("09:00",), set()), ["2026-05-09 09:00"])

    def test_observation_not_due_before_scheduled_time(self) -> None:
        now = datetime(2026, 5, 9, 8, 59)

        self.assertEqual(_due_observation_keys(now, ("09:00",), set()), [])

    def test_observation_not_due_after_sent(self) -> None:
        now = datetime(2026, 5, 9, 12, 30)

        self.assertEqual(_due_observation_keys(now, ("09:00",), {"2026-05-09 09:00"}), [])


if __name__ == "__main__":
    unittest.main()
