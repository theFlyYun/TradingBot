# 多市场半自动交易提醒系统

这是根据视频转写复现并逐步工程化的 v1：用财务指标和技术指标维护股票池，按固定周期生成买卖观察，通过飞书通知，最后由人手动打开券商软件确认下单。

它不是自动下单机器人，默认不连接券商账户，也不会执行真实交易。

## 策略规则

股票池筛选：

- PE `< 20`
- 股息率 `> 4%`
- ROE `> 10%`
- 市值达到配置阈值

定时监控买卖时机：

- 买入候选：收盘价 `< MA120 * 0.88` 且 `RSI < 30`
- 卖出候选：收盘价 `> MA120 * 1.12` 且 `RSI > 70`
- 成交量确认可在 `config.toml` 里打开

## 使用

安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

可选：以可编辑模式安装项目，方便后续工程化开发：

```bash
python3 -m pip install -e ".[dev]"
```

常用开发命令：

```bash
make test
make compile
make monitor-once
make warehouse-sample
```

生成 watchlist：

```bash
python3 -m tradingbot.screen
```

刷新最新可用财务数据后再筛选：

```bash
export ALPHAVANTAGE_API_KEY="你的 Alpha Vantage API Key"
python3 -m tradingbot.live_fundamentals --provider alpha_vantage
python3 -m tradingbot.screen
```

注意：财务数据不是逐秒实时数据，PE、ROE、股息率和市值依赖交易所/财报/数据商更新。这里的“实时”指每次运行时向数据商拉取最新可用值。

每日监控：

```bash
python3 -m tradingbot.monitor
```

周期性拉取行情并分析，默认每 30 分钟一轮：

```bash
python3 -m tradingbot.scheduler
```

周期性刷新财务数据并分析：

```bash
export ALPHAVANTAGE_API_KEY="你的 Alpha Vantage API Key"
python3 -m tradingbot.scheduler \
  --refresh-fundamentals \
  --fundamentals-interval-hours 24 \
  --monitor-interval-minutes 5
```

先测试一轮并退出：

```bash
python3 -m tradingbot.scheduler --once
```

临时指定股票，支持多个市场的 Yahoo Finance 可识别代码：

```bash
python3 -m tradingbot.monitor --symbols AAPL MSFT 0700.HK 601126.SS
```

行情源、缓存和并发在 `config.toml` 的 `[market_data]` 中配置：

```toml
[market_data]
provider = "yahoo"
price_range = "1y"
interval = "1d"
request_timeout_seconds = 20
cache_ttl_seconds = 180
max_workers = 10
```

行情和信号结果会写入本地 Parquet 仓库，方便 DuckDB 查询和后续回测：

```text
data/warehouse/
  prices/provider=yahoo/interval=1d/symbol=AAPL.parquet
  signals/run_date=YYYY-MM-DD/signals.parquet
```

查询本地历史行情：

```bash
python3 -m tradingbot.warehouse prices --symbols AAPL MSFT --start 2024-01-01
```

查看单只股票过去两年的触发点：

```bash
python3 -m tradingbot.backtest AAPL
```

## 飞书通知

设置 webhook 后运行 monitor：

```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/..."
python3 -m tradingbot.monitor
```

没有 webhook 时，程序只写本地 CSV 报告，不发送消息。

默认只有出现 `BUY` / `SELL` 信号才发送飞书消息；无信号不打扰。如果希望每轮都发“无信号”消息，把 `config.toml` 里的 `notify_on_empty` 改成 `true`。

定时播报会记住上一次触发 `BUY` / `SELL` 的股票集合。只有买入/卖出股票集合发生变化，或手动执行 `alert`，才会再次发送交易提醒。

## 大模型分析

项目预留了统一 LLM 接口，当前支持 DeepSeek Chat Completions API 和 OpenAI Responses API。大模型只负责解释、总结、风控检查和自然语言问答，不作为行情源，也不直接决定真实下单。

启用方式：

```toml
[llm]
enabled = true
provider = "deepseek"
model = "deepseek-v4-flash"
```

密钥写入本地 `.env`：

```bash
TRADINGBOT_LLM_PROVIDER="deepseek"
DEEPSEEK_API_KEY="sk-..."
DEEPSEEK_MODEL="deepseek-v4-flash"
```

启用后，交易提醒链路变为：

```text
行情数据 -> 策略计算 -> 大模型解释/总结/风控检查 -> 飞书通知/交互问答
```

北京时间每日 09:00 和 20:30 可以发送市场观察报告：

```toml
[observation]
enabled = true
times = ["09:00", "20:30"]
```

如果你的飞书没有“自定义机器人”，可以用自建应用模式。先用 `cc-connect feishu setup --project my-codex` 创建应用，再把应用信息写入 `.env`：

```bash
FEISHU_WEBHOOK_URL=""
FEISHU_APP_ID="cli_xxxxxxxxxxxx"
FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxx"
FEISHU_RECEIVE_ID="ou_xxxxxxxxxxxx"
FEISHU_RECEIVE_ID_TYPE="open_id"
```

私聊用 `open_id`，群聊用 `chat_id`。配置好后测试：

```bash
python3 -m tradingbot.test_feishu
```

## Mac 常驻运行

复制环境变量模板：

```bash
cp .env.example .env
```

如果需要飞书提醒，编辑 `.env`，填入：

```bash
FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/..."
```

启动：

```bash
scripts/start.sh
```

指定间隔启动，例如 5 分钟：

```bash
scripts/start.sh 5
```

查看状态：

```bash
scripts/status.sh
```

停止：

```bash
scripts/stop.sh
```

启动脚本使用 `caffeinate -dimsu` 尽量保持 Mac 唤醒。macOS 对“合盖继续运行”有限制：建议接电源使用；部分 MacBook 合盖后仍需要外接显示器/键鼠才能保持 clamshell 模式，纯电池合盖可能被系统强制睡眠。

如果项目位于 `Documents` 目录，macOS 的 LaunchAgent 可能无法后台访问。当前已使用运行副本：

```bash
/Users/longyunfei/tradingbot-runtime
```

后台启动、停止和查看状态建议使用 runtime 里的脚本：

```bash
/Users/longyunfei/tradingbot-runtime/scripts/start.sh 30
/Users/longyunfei/tradingbot-runtime/scripts/status.sh
/Users/longyunfei/tradingbot-runtime/scripts/stop.sh
```

## 指令通路

当前飞书自定义机器人 webhook 只能发消息，不能直接接收群聊消息。本项目已实现指令核心和本地 HTTP 触发通路：

```bash
python3 -m tradingbot.command "tradingbot help"
python3 -m tradingbot.command "tradingbot watchlist"
```

也可以启动本地指令服务：

```bash
scripts/start_command_server.sh 8787
```

本地触发：

```bash
curl -X POST http://127.0.0.1:8787/command \
  -H 'Content-Type: application/json' \
  -d '{"text":"tradingbot watchlist"}'
```

可用指令：

- `tradingbot help`：显示可用指令和使用方法
- `tradingbot watchlist`：显示当前 Watchlist
- `tradingbot alert`：立即拉取行情并发送当前交易提醒
- `tradingbot ai 你的问题`：通过大模型自然语言查询 watchlist、信号和项目上下文

当前已接入 cc-connect，飞书里可用：

```text
/tb help
/tb watchlist
/tb alert
/tb ai 当前 watchlist 有哪些风险？
/tbhelp
/tbwatchlist
```

## 文件

- `config.toml`：筛选阈值、信号阈值、通知配置
- `data/symbols.csv`：要刷财务数据的股票代码列表
- `data/universe.csv`：基础股票池和财务数据，建议每周人工/脚本更新
- `data/watchlist.csv`：筛选后的股票池
- `reports/signals_YYYY-MM-DD.csv`：每日监控结果，本地生成，不提交到 Git

## 项目结构

```text
tradingbot/
  data.py              # 行情 provider 和本地缓存入口
  storage.py           # DuckDB / Parquet 本地仓库
  monitor.py           # 当前交易提醒运行主流程
  notify.py            # 飞书与 webhook 通知
  llm/                 # OpenAI/后续大模型 provider 统一接口
  strategy.py          # 当前 MA/RSI 策略，保留兼容入口
  strategies/          # 后续多策略注册与组合
  backtesting/         # 后续回测引擎、交易记录、收益曲线
  research/            # 后续研究脚本和 notebook 辅助函数
tests/                 # 基础单元测试
docs/                  # 架构与路线说明
notebooks/             # 后续研究 notebook
experiments/           # 后续参数实验、策略试验
```
