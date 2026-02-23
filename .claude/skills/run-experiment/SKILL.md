---
name: run-experiment
description: 実験を実行する。pytest → docker compose up → 実験結果表示
allowed-tools: Bash, Read
context: fork
agent: general-purpose
---
実験を実行します。引数: $ARGUMENTS

現在のテスト状況: !`uv run pytest -q --tb=no 2>&1 | tail -5`

1. uv run pytest -q でテストを実行
2. docker compose up -d でコンテナ起動
3. 実験を実行 (引数があれば使用: $ARGUMENTS)
4. 結果を表示
