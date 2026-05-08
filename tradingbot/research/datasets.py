from __future__ import annotations

import pandas as pd

from tradingbot.config import load_config
from tradingbot.storage import Warehouse


def load_prices(
    symbols: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
    config_path: str = "config.toml",
) -> pd.DataFrame:
    config = load_config(config_path)
    warehouse = Warehouse(config.runtime.warehouse_dir)
    return warehouse.query_prices(symbols=symbols, start=start, end=end)
