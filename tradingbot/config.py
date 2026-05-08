from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import tomllib


@dataclass(frozen=True)
class ScreeningConfig:
    max_pe: float
    min_dividend_yield: float
    min_roe: float
    min_market_cap_hkd: float


@dataclass(frozen=True)
class SignalConfig:
    ma_window: int
    rsi_window: int
    buy_below_ma120: float
    sell_above_ma120: float
    buy_rsi_below: float
    sell_rsi_above: float
    volume_window: int
    min_volume_ratio: float
    require_volume_confirmation: bool


@dataclass(frozen=True)
class RuntimeConfig:
    symbols_csv: Path
    universe_csv: Path
    watchlist_csv: Path
    reports_dir: Path
    warehouse_dir: Path


@dataclass(frozen=True)
class FundamentalsConfig:
    provider: str
    api_key: str


@dataclass(frozen=True)
class MarketDataConfig:
    provider: str
    price_range: str
    interval: str
    request_timeout_seconds: float
    cache_ttl_seconds: int
    max_workers: int


@dataclass(frozen=True)
class SchedulerConfig:
    monitor_interval_minutes: float
    fundamentals_interval_hours: float
    refresh_fundamentals: bool


@dataclass(frozen=True)
class FeishuConfig:
    webhook_url: str
    webhook_whitelist: tuple[str, ...]
    notify_on_empty: bool
    custom_keyword: str
    app_id: str
    app_secret: str
    receive_id: str
    receive_id_type: str
    chat_whitelist: tuple[str, ...]


@dataclass(frozen=True)
class AppConfig:
    screening: ScreeningConfig
    signals: SignalConfig
    runtime: RuntimeConfig
    fundamentals: FundamentalsConfig
    market_data: MarketDataConfig
    scheduler: SchedulerConfig
    feishu: FeishuConfig


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_config(path: str | Path = "config.toml") -> AppConfig:
    config_path = Path(path)
    _load_env_file(config_path.parent / ".env")
    raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    base = config_path.parent

    runtime = raw["runtime"]
    feishu = raw.get("feishu", {})
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL", feishu.get("webhook_url", ""))
    webhook_whitelist = tuple(str(value) for value in feishu.get("webhook_whitelist", []) if value)
    if webhook_url:
        webhook_whitelist = (webhook_url, *webhook_whitelist)
    fundamentals = raw.get("fundamentals", {})
    market_data = raw.get("market_data", {})
    scheduler = raw.get("scheduler", {})

    return AppConfig(
        screening=ScreeningConfig(**raw["screening"]),
        signals=SignalConfig(**raw["signals"]),
        runtime=RuntimeConfig(
            symbols_csv=(base / runtime["symbols_csv"]).resolve(),
            universe_csv=(base / runtime["universe_csv"]).resolve(),
            watchlist_csv=(base / runtime["watchlist_csv"]).resolve(),
            reports_dir=(base / runtime["reports_dir"]).resolve(),
            warehouse_dir=(base / runtime.get("warehouse_dir", "data/warehouse")).resolve(),
        ),
        fundamentals=FundamentalsConfig(
            provider=fundamentals.get("provider", "csv"),
            api_key=os.getenv("ALPHAVANTAGE_API_KEY", fundamentals.get("api_key", "")),
        ),
        market_data=MarketDataConfig(
            provider=market_data.get("provider", "yahoo"),
            price_range=market_data.get("price_range", "1y"),
            interval=market_data.get("interval", "1d"),
            request_timeout_seconds=float(market_data.get("request_timeout_seconds", 20)),
            cache_ttl_seconds=int(market_data.get("cache_ttl_seconds", 180)),
            max_workers=int(market_data.get("max_workers", 10)),
        ),
        scheduler=SchedulerConfig(
            monitor_interval_minutes=float(scheduler.get("monitor_interval_minutes", 60)),
            fundamentals_interval_hours=float(scheduler.get("fundamentals_interval_hours", 24)),
            refresh_fundamentals=bool(scheduler.get("refresh_fundamentals", False)),
        ),
        feishu=FeishuConfig(
            webhook_url=webhook_url,
            webhook_whitelist=webhook_whitelist,
            notify_on_empty=bool(feishu.get("notify_on_empty", False)),
            custom_keyword=os.getenv("FEISHU_CUSTOM_KEYWORD", feishu.get("custom_keyword", "tradingbot")),
            app_id=os.getenv("FEISHU_APP_ID", feishu.get("app_id", "")),
            app_secret=os.getenv("FEISHU_APP_SECRET", feishu.get("app_secret", "")),
            receive_id=os.getenv("FEISHU_RECEIVE_ID", feishu.get("receive_id", "")),
            receive_id_type=os.getenv("FEISHU_RECEIVE_ID_TYPE", feishu.get("receive_id_type", "open_id")),
            chat_whitelist=tuple(str(value) for value in feishu.get("chat_whitelist", []) if value),
        ),
    )
