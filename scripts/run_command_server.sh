#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${1:-8787}"

cd "$ROOT"
exec python3 -u -m hkbot.command_server --port "$PORT"
