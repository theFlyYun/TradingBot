# Runtime Module

The project can run as a local Mac background process. The runtime copy is used because macOS may restrict background access to projects under `Documents`.

## Runtime Path

```bash
/Users/longyunfei/tradingbot-runtime
```

## Start, Status, Stop

```bash
/Users/longyunfei/tradingbot-runtime/scripts/start.sh 30
/Users/longyunfei/tradingbot-runtime/scripts/status.sh
/Users/longyunfei/tradingbot-runtime/scripts/stop.sh
```

From inside the project directory, prefix scripts with `./`:

```bash
./scripts/status.sh
```

## Keep Mac Awake

`scripts/start.sh` uses `caffeinate -dimsu` to keep the Mac awake where macOS allows it.

MacBook closed-lid behavior is still controlled by macOS and hardware mode. For reliable closed-lid operation, use power and clamshell mode with external display/keyboard/mouse when needed.
