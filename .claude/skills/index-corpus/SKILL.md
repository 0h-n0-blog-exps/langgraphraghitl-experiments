---
name: index-corpus
description: 国会議事録コーパスを OpenSearch Serverless にインデックス（RAG用ベクトル化）
allowed-tools: Bash, Read
context: fork
---
国会議事録コーパスを OpenSearch Serverless にインデックスします。

現在のコーパス: !`ls data/corpus/ 2>/dev/null | wc -l` 件

AWS リソースが必要です。事前に /deploy-aws を実行してください。

1. data/corpus/ のドキュメントを確認
2. ベクトル埋め込みを生成（Ollama または Bedrock）
3. OpenSearch Serverless にインデックス
4. インデックス結果を確認
