---
name: hitl-review
description: HITL (Human-In-The-Loop) レビューキューを確認し、保留中のクエリを承認・却下する
allowed-tools: Bash, Read
context: fork
agent: general-purpose
---
HITL レビューキューを確認します。

現在のレビュー待ちクエリ: !`uv run python -c "from src.langgraph_rag_hitl.core import get_pending_reviews; import json; print(json.dumps(get_pending_reviews(), indent=2, ensure_ascii=False))" 2>/dev/null || echo "レビューキューなし"`

引数 (クエリID or all): $ARGUMENTS

1. レビュー待ちクエリを一覧表示
2. 各クエリの内容・スコア・理由を確認
3. 承認または却下を実施
4. 承認済みの場合は生成を再開
