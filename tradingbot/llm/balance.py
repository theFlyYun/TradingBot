from __future__ import annotations

import argparse
from dataclasses import dataclass

import requests

from ..config import LLMConfig, load_config


@dataclass(frozen=True)
class BalanceInfo:
    currency: str
    total_balance: str
    granted_balance: str
    topped_up_balance: str


@dataclass(frozen=True)
class DeepSeekBalance:
    is_available: bool
    balances: tuple[BalanceInfo, ...]


def fetch_deepseek_balance(config: LLMConfig) -> DeepSeekBalance:
    if config.provider != "deepseek":
        raise ValueError(f"DeepSeek balance requires provider=deepseek, got {config.provider}")
    if not config.api_key:
        raise ValueError("DEEPSEEK_API_KEY is not configured")

    response = requests.get(
        f"{config.base_url.rstrip('/')}/user/balance",
        headers={"Authorization": f"Bearer {config.api_key}"},
        timeout=config.timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    return parse_deepseek_balance(payload)


def parse_deepseek_balance(payload: dict[str, object]) -> DeepSeekBalance:
    raw_balances = payload.get("balance_infos", [])
    balances: list[BalanceInfo] = []
    if isinstance(raw_balances, list):
        for item in raw_balances:
            if not isinstance(item, dict):
                continue
            balances.append(
                BalanceInfo(
                    currency=str(item.get("currency", "")),
                    total_balance=str(item.get("total_balance", "")),
                    granted_balance=str(item.get("granted_balance", "")),
                    topped_up_balance=str(item.get("topped_up_balance", "")),
                )
            )
    return DeepSeekBalance(
        is_available=bool(payload.get("is_available", False)),
        balances=tuple(balances),
    )


def format_deepseek_balance(balance: DeepSeekBalance) -> str:
    lines = [f"DeepSeek API 可用：{str(balance.is_available).lower()}"]
    if not balance.balances:
        lines.append("余额：未返回余额信息")
        return "\n".join(lines)
    for item in balance.balances:
        lines.extend(
            [
                f"币种：{item.currency or '-'}",
                f"总余额：{item.total_balance or '-'}",
                f"赠送余额：{item.granted_balance or '-'}",
                f"充值余额：{item.topped_up_balance or '-'}",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check DeepSeek API balance without printing the API key.")
    parser.add_argument("--config", default="config.toml", help="Path to config.toml. The sibling .env is loaded automatically.")
    args = parser.parse_args()

    config = load_config(args.config)
    balance = fetch_deepseek_balance(config.llm)
    print(format_deepseek_balance(balance))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
