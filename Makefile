.PHONY: test compile monitor-once warehouse-sample status

test:
	python3 -m unittest discover -s tests

compile:
	python3 -m compileall hkbot tests

monitor-once:
	python3 -m hkbot.monitor --symbols AAPL MSFT --max-workers 2 --cache-ttl-seconds 180

warehouse-sample:
	python3 -m hkbot.warehouse prices --symbols AAPL MSFT --limit 5

status:
	scripts/status.sh
