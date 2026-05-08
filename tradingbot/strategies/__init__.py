"""Strategy package.

The live alert runtime still imports `tradingbot.strategy` for backward compatibility.
Future strategies can live under this package and be exposed through a registry.
"""

from tradingbot.strategy import MaRsiStrategy, TradingStrategy, build_strategy

__all__ = ["MaRsiStrategy", "TradingStrategy", "build_strategy"]
