---
name: test-ui
description: Playwright E2E テストを実行して UI の不具合を検出・修正する
allowed-tools: Bash, Read, Write, Edit
context: fork
---
Playwright E2E テストを実行します。

現在の状態:
- package.json: !`cat frontend/package.json | jq '.scripts["test:e2e"]' 2>/dev/null`
- playwright config: !`test -f frontend/playwright.config.ts && echo "found" || echo "not found"`

1. docker compose up -d でフルスタック起動
2. cd frontend && npm run test:e2e を実行
3. 失敗したテストを修正
4. 全テスト PASS まで繰り返す (最大3回)
