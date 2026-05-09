from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .commands import command_name, handle_command
from .config import load_config


@dataclass(frozen=True)
class Check:
    name: str
    run: Callable[[], None]


def _run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _check_config(config_path: Path) -> None:
    config = load_config(config_path)
    required_paths = [
        config.runtime.symbols_csv,
        config.runtime.universe_csv,
        config.runtime.watchlist_csv,
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise AssertionError(f"missing configured data files: {', '.join(missing)}")


def _check_command_routing(config_path: Path) -> None:
    config = load_config(config_path)
    expected = {
        "help": "help",
        "info": "info",
        "watchlist": "watchlist",
        "wl": "watchlist",
        "alert": "alert",
        "ai hi": "ai",
    }
    for text, name in expected.items():
        actual = command_name(text, config.feishu.custom_keyword)
        if actual != name:
            raise AssertionError(f"{text!r} routed to {actual!r}, expected {name!r}")
    if command_name("tbai hi", config.feishu.custom_keyword) is not None:
        raise AssertionError("'tbai hi' should not be treated as a tradingbot command")


def _check_command_smoke(config_path: Path) -> None:
    config = load_config(config_path)
    for text, expected in (
        ("help", "tradingbot 指令帮助"),
        ("info", "tradingbot 基础信息"),
        ("watchlist", "tradingbot 当前 Watchlist"),
    ):
        result = handle_command(text, config)
        if expected not in result.text:
            raise AssertionError(f"{text!r} output did not include {expected!r}")


def _check_sensitive_files(root: Path) -> None:
    patterns = tuple(
        re.compile(pattern)
        for pattern in (
            r"sk-proj-[A-Za-z0-9_-]{20,}",
            r"sk-[A-Za-z0-9]{20,}",
            r'app_secret\s*=\s*"vinAPI[A-Za-z0-9_-]+',
            r"cli_a97164[A-Za-z0-9_-]+",
            r"oc_b5844[A-Za-z0-9_-]+",
            r"c3bf6600-[A-Za-z0-9-]+",
        )
    )
    excluded_dirs = {".git", ".cache", "data/warehouse", "logs", "reports", "run", "__pycache__"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.name == ".env" or relative.name.startswith(".env."):
            continue
        if any(str(relative).startswith(prefix) for prefix in excluded_dirs):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in patterns:
            if pattern.search(text):
                raise AssertionError(f"sensitive-looking value matching {pattern.pattern!r} found in {relative}")


def _check_runtime(runtime_dir: Path) -> None:
    config_path = runtime_dir / "config.toml"
    if not config_path.exists():
        raise AssertionError(f"runtime config not found: {config_path}")
    _check_config(config_path)
    config = load_config(config_path)
    payload = {
        "llm_enabled": config.llm.enabled,
        "llm_provider": config.llm.provider,
        "llm_key_configured": bool(config.llm.api_key),
        "observation_enabled": config.observation.enabled,
        "observation_times": config.observation.times,
        "chat_targets": len(config.feishu.chat_whitelist),
        "webhook_targets": len(config.feishu.webhook_whitelist),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_checks(mode: str, config_path: Path, runtime_dir: Path) -> list[Check]:
    root = _project_root()
    checks = [
        Check("config", lambda: _check_config(config_path)),
        Check("commands", lambda: _check_command_routing(config_path)),
        Check("command-smoke", lambda: _check_command_smoke(config_path)),
    ]
    if mode in {"check", "all"}:
        checks.extend(
            [
                Check("unit-tests", lambda: _run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], root)),
                Check("compile", lambda: _run([sys.executable, "-m", "compileall", "tradingbot", "tests"], root)),
                Check("sensitive-scan", lambda: _check_sensitive_files(root)),
            ]
        )
    if mode in {"runtime", "all"}:
        checks.append(Check("runtime", lambda: _check_runtime(runtime_dir)))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Run modular tradingbot health checks.")
    parser.add_argument("--mode", choices=("smoke", "check", "runtime", "all"), default="smoke")
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--runtime-dir", default="/Users/longyunfei/tradingbot-runtime")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    runtime_dir = Path(args.runtime_dir).resolve()
    for check in build_checks(args.mode, config_path, runtime_dir):
        print(f"[doctor] {check.name} ...", end=" ", flush=True)
        check.run()
        print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
