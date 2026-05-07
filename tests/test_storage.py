from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import pandas as pd

from hkbot.storage import Warehouse, read_parquet


class WarehouseTest(unittest.TestCase):
    def test_write_prices_merges_by_symbol_and_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            warehouse = Warehouse(Path(tmp))
            first = pd.DataFrame(
                [
                    {"symbol": "AAPL", "date": "2026-01-01", "close": 100.0},
                    {"symbol": "AAPL", "date": "2026-01-02", "close": 101.0},
                ]
            )
            second = pd.DataFrame(
                [
                    {"symbol": "AAPL", "date": "2026-01-02", "close": 102.0},
                    {"symbol": "AAPL", "date": "2026-01-03", "close": 103.0},
                ]
            )

            path = warehouse.write_prices(first, "yahoo", "1d", "AAPL")
            warehouse.write_prices(second, "yahoo", "1d", "AAPL")
            result = read_parquet(path)

        self.assertEqual(len(result), 3)
        dates = result["date"].astype(str)
        self.assertEqual(result.loc[dates == "2026-01-02", "close"].iloc[0], 102.0)

    def test_query_prices_filters_symbol_and_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            warehouse = Warehouse(Path(tmp))
            warehouse.write_prices(
                pd.DataFrame(
                    [
                        {"symbol": "AAPL", "date": "2026-01-01", "close": 100.0},
                        {"symbol": "AAPL", "date": "2026-01-02", "close": 101.0},
                    ]
                ),
                "yahoo",
                "1d",
                "AAPL",
            )
            warehouse.write_prices(
                pd.DataFrame([{"symbol": "MSFT", "date": "2026-01-02", "close": 200.0}]),
                "yahoo",
                "1d",
                "MSFT",
            )

            result = warehouse.query_prices(symbols=["AAPL"], start="2026-01-02")

        self.assertEqual(result["symbol"].tolist(), ["AAPL"])
        self.assertEqual(result["date"].astype(str).tolist(), ["2026-01-02"])


if __name__ == "__main__":
    unittest.main()
