# 多市场半自动交易提醒系统

这是一个多市场半自动交易提醒和研究项目：维护股票池，定时拉取行情，生成买卖观察，通过飞书通知，并逐步扩展到回测、研究报告和风险分析。

它不是自动下单机器人，默认不连接券商账户，也不会执行真实交易。当前所有信号都只作为人工复核前的观察提示。

## Quick Start

安装依赖：

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -e ".[dev]"
```

常用开发检查：

```bash
make test
make check
make smoke
make check-runtime
```

生成 watchlist：

```bash
python3 -m tradingbot.screen
```

跑一轮交易提醒：

```bash
python3 -m tradingbot.monitor
```

启动定时监控：

```bash
python3 -m tradingbot.scheduler
```

运行回测：

```bash
python3 -m pip install -e ".[research]"
python3 -m tradingbot.backtesting.run --symbols AAPL --start 2024-01-01 --end 2026-05-10
```

## Runtime

当前推荐使用运行副本，避免 macOS 对 `Documents` 目录后台访问的限制：

```bash
/Users/longyunfei/tradingbot-runtime/scripts/start.sh 30
/Users/longyunfei/tradingbot-runtime/scripts/status.sh
/Users/longyunfei/tradingbot-runtime/scripts/stop.sh
```

## Documentation

项目文档按模块维护，入口见 [docs/README.md](docs/README.md)。

- [策略](docs/modules/strategy.md)：股票池筛选、MA/RSI 信号逻辑。
- [数据仓库](docs/modules/data-warehouse.md)：DuckDB/Parquet 本地行情仓库。
- [回测](docs/modules/backtesting.md)：VectorBT v1 回测命令、假设和报告输出。
- [通知](docs/modules/notifications.md)：飞书 webhook/app 通知和重复提醒抑制。
- [大模型](docs/modules/llm.md)：DeepSeek/OpenAI 接口、AI 分析和市场观察。
- [运行](docs/modules/runtime.md)：Mac 后台运行、启动、停止、状态查看。
- [指令](docs/modules/commands.md)：本地命令、HTTP 指令服务、cc-connect 飞书指令。
- [架构](docs/ARCHITECTURE.md)：模块边界和扩展方向。
- [路线图](docs/ROADMAP.md)：后续计划。

## Project Layout

```text
tradingbot/
  data.py              # 行情 provider 和本地缓存入口
  storage.py           # DuckDB / Parquet 本地仓库
  monitor.py           # 当前交易提醒运行主流程
  notify.py            # 飞书与 webhook 通知
  llm/                 # DeepSeek/OpenAI/后续大模型 provider 统一接口
  strategy.py          # 当前 MA/RSI 策略，保留兼容入口
  strategies/          # 后续多策略注册与组合
  backtesting/         # VectorBT 回测入口、信号转换、报告输出
  research/            # 后续研究脚本和 notebook 辅助函数
tests/                 # 基础单元测试
docs/                  # 架构、路线图和模块文档
```

## Documentation Rule

后续新增或修改模块能力时，优先更新 `docs/modules/<module>.md`。只有入口命令、安装方式或文档索引变化时，再更新本 README。
