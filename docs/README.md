# Documentation Index

This directory keeps project documentation split by module. The top-level README is only the product entry point; module details live here so each area can grow independently.

## Core Docs

- [Architecture](ARCHITECTURE.md): runtime flow, extension areas, and module boundaries.
- [Roadmap](ROADMAP.md): planned work and future modules.

## Module Docs

- [Strategy](modules/strategy.md): current screening rules and MA/RSI signal logic.
- [Data Warehouse](modules/data-warehouse.md): DuckDB/Parquet storage layout and local query usage.
- [Backtesting](modules/backtesting.md): VectorBT v1 usage, assumptions, outputs, and caveats.
- [Notifications](modules/notifications.md): Feishu webhook/app notifications and duplicate suppression.
- [LLM](modules/llm.md): DeepSeek/OpenAI integration, AI analysis, and market observations.
- [Runtime](modules/runtime.md): Mac background runtime, start/stop/status, and runtime copy.
- [Commands](modules/commands.md): local command route and cc-connect Feishu commands.

## Maintenance Rule

When a module gains new behavior, update that module's doc in `docs/modules/` first. Only update the top-level README when the public entry point, quick-start flow, or doc index changes.
