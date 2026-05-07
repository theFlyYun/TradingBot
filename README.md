# 港股半自动交易提醒系统

这是根据视频转写复现的 v1：财务指标筛选股票池，每日用 MA120 乖离率和 RSI 生成买卖提醒，通过飞书通知，最后由人手动打开券商软件下单。

它不是自动下单机器人，默认不连接券商账户，也不会执行真实交易。

## 策略规则

每周筛选股票池：

- PE `< 20`
- 股息率 `> 4%`
- ROE `> 10%`
- 市值 `> 1000 亿港币`

每日监控买卖时机：

- 买入候选：收盘价 `< MA120 * 0.88` 且 `RSI < 30`
- 卖出候选：收盘价 `> MA120 * 1.12` 且 `RSI > 70`
- 成交量确认可在 `config.toml` 里打开

## 使用

安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

每周生成 watchlist：

```bash
python3 -m hkbot.screen
```

刷新最新可用财务数据后再筛选：

```bash
export ALPHAVANTAGE_API_KEY="你的 Alpha Vantage API Key"
python3 -m hkbot.live_fundamentals --provider alpha_vantage
python3 -m hkbot.screen
```

注意：财务数据不是逐秒实时数据，PE、ROE、股息率和市值依赖交易所/财报/数据商更新。这里的“实时”指每次运行时向数据商拉取最新可用值。

每日监控：

```bash
python3 -m hkbot.monitor
```

周期性拉取行情并分析，默认每 30 分钟一轮：

```bash
python3 -m hkbot.scheduler
```

周期性刷新财务数据并分析：

```bash
export ALPHAVANTAGE_API_KEY="你的 Alpha Vantage API Key"
python3 -m hkbot.scheduler \
  --refresh-fundamentals \
  --fundamentals-interval-hours 24 \
  --monitor-interval-minutes 5
```

先测试一轮并退出：

```bash
python3 -m hkbot.scheduler --once
```

临时指定股票：

```bash
python3 -m hkbot.monitor --symbols 0005.HK 0939.HK 0883.HK
```

查看单只股票过去两年的触发点：

```bash
python3 -m hkbot.backtest 0005.HK
```

## 飞书通知

设置 webhook 后运行 monitor：

```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/..."
python3 -m hkbot.monitor
```

没有 webhook 时，程序只写本地 CSV 报告，不发送消息。

默认只有出现 `BUY` / `SELL` 信号才发送飞书消息；无信号不打扰。如果希望每轮都发“无信号”消息，把 `config.toml` 里的 `notify_on_empty` 改成 `true`。

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
python3 -m hkbot.test_feishu
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
python3 -m hkbot.command "tradingbot help"
python3 -m hkbot.command "tradingbot watchlist"
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

当前已接入 cc-connect，飞书里可用：

```text
/tb help
/tb watchlist
/tb alert
/tbhelp
/tbwatchlist
```

## 文件

- `config.toml`：筛选阈值、信号阈值、通知配置
- `data/symbols.csv`：要刷财务数据的股票代码列表
- `data/universe.csv`：基础股票池和财务数据，建议每周人工/脚本更新
- `data/watchlist.csv`：筛选后的股票池
- `reports/signals_YYYY-MM-DD.csv`：每日监控结果，本地生成，不提交到 Git
