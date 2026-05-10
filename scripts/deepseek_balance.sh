#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${1:-$ROOT_DIR/config.toml}"

cd "$ROOT_DIR"
python3 -m tradingbot.llm.balance --config "$CONFIG_PATH"
