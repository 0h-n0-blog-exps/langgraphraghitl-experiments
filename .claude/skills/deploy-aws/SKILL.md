---
name: deploy-aws
description: Terraform で AWS にデプロイ。API Gateway + Lambda + S3 + OpenSearch Serverless を作成
allowed-tools: Bash, Read
disable-model-invocation: true
argument-hint: "[anthropic_api_key]"
---
AWS リソースを作成します。課金が発生します。

現在の Terraform 状態: !`cd terraform && terraform show 2>/dev/null | head -20 || echo "未デプロイ"`

引数 (APIキー): $ARGUMENTS

1. terraform init
2. terraform plan -var="anthropic_api_key=$ARGUMENTS" -var="project_name=langgraph-rag-hitl"
3. 内容を確認してから apply
4. outputs の api_gateway_url を frontend/.env.local に書き込む
5. 実験後は /destroy-aws を実行してリソース削除
