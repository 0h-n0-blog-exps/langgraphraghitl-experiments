---
name: setup-data
description: 国会議事録コーパス(500件)をダウンロードして data/corpus/ に保存する
allowed-tools: Bash
context: fork
---
国会議事録コーパスをダウンロードします:

現在の状態: !`ls data/corpus/ 2>/dev/null | wc -l` 件

1. uv run data/download.py を実行
2. data/corpus/ に JSONL 形式で 500件保存
3. 完了後: !`ls data/corpus/ | wc -l` 件を確認してレポート
