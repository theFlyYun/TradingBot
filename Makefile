.PHONY: test compile check smoke check-runtime monitor-once warehouse-sample balance status

test:
	python3 -m unittest discover -s tests

compile:
	python3 -m compileall tradingbot tests

check:
	python3 -m tradingbot.doctor --mode check

smoke:
	python3 -m tradingbot.doctor --mode smoke

check-runtime:
	python3 -m tradingbot.doctor --mode runtime --config /Users/longyunfei/tradingbot-runtime/config.toml

monitor-once:
	python3 -m tradingbot.monitor --symbols AAPL MSFT --max-workers 2 --cache-ttl-seconds 180

warehouse-sample:
	python3 -m tradingbot.warehouse prices --symbols AAPL MSFT --limit 5

balance:
	python3 -m tradingbot.llm.balance --config /Users/longyunfei/tradingbot-runtime/config.toml

status:
	scripts/status.sh
