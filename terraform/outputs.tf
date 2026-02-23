# [DEBUG] ============================================================
# Agent   : architect
# Task    : Terraform + Docker + docker-compose 設定
# Created : 2026-02-23T18:56:02
# Updated : 2026-02-23T18:56:02
# [/DEBUG] ===========================================================

output "api_gateway_url" {
  description = "API Gateway HTTP API のエンドポイント URL。Vercel の API_URL 環境変数に設定する。"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "lambda_function_name" {
  description = "Lambda 関数名。ECR イメージ更新後の手動デプロイ時に使用する。"
  value       = aws_lambda_function.api.function_name
}

output "s3_bucket_name" {
  description = "実験結果・RAG ドキュメント保存バケット名。"
  value       = aws_s3_bucket.experiments.id
}

output "opensearch_endpoint" {
  description = "OpenSearch Serverless コレクションエンドポイント。インデックス作成・検索 API に使用する。"
  value       = aws_opensearchserverless_collection.rag.collection_endpoint
}

output "opensearch_collection_arn" {
  description = "OpenSearch Serverless コレクション ARN。IAM ポリシーの設定に使用する。"
  value       = aws_opensearchserverless_collection.rag.arn
}

output "lambda_exec_role_arn" {
  description = "Lambda 実行ロール ARN。OpenSearch Serverless データアクセスポリシーの追加設定時に参照する。"
  value       = aws_iam_role.lambda_exec.arn
}
