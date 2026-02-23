# [DEBUG] ============================================================
# Agent   : architect
# Task    : Terraform + Docker + docker-compose 設定
# Created : 2026-02-23T18:56:02
# Updated : 2026-02-23
# [/DEBUG] ===========================================================

variable "aws_region" {
  type        = string
  description = "AWS リージョン。Lambda, API Gateway, S3, OpenSearch Serverless のデプロイ先。"
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "プロジェクト名。全リソースのタグ・命名に使用される。"
  default     = "langgraph-rag-hitl"
}

variable "anthropic_api_key" {
  type        = string
  description = "Anthropic API キー。Lambda の環境変数として渡す。secrets のため default なし。"
  sensitive   = true
}

variable "lambda_image_uri" {
  type        = string
  description = "Lambda コンテナイメージの URI（ECR リポジトリ URI:タグ形式）。CI/CD パイプラインでプッシュ後に指定する。"
  default     = "placeholder:latest"
}

variable "lambda_reserved_concurrent_executions" {
  type        = number
  description = "Lambda 関数の予約済み同時実行数。0 はすべてのリクエストを拒否（一時停止）。-1 は制限なし（コスト爆発リスクあり）のため使用禁止。"
  default     = 10
}

variable "opensearch_data_access_principal" {
  type        = list(string)
  description = "OpenSearch Serverless データアクセスポリシーで許可するプリンシパル ARN のリスト（例: Lambda 実行ロール ARN）。デプロイ後に追加設定が必要。"
  default     = []
}

variable "s3_force_destroy" {
  type        = bool
  description = "terraform destroy 時に S3 バケット内のオブジェクトを強制削除するか。実験リポジトリのため true を推奨するが、本番では false にすること。"
  default     = true
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch Logs グループのログ保持日数。コスト削減のため短く設定する。"
  default     = 30
}

variable "cors_allowed_origins" {
  type        = list(string)
  description = "API Gateway CORS で許可するオリジンのリスト。本番では Vercel デプロイ URL 等を指定すること（例: [\"https://your-app.vercel.app\"]）。デフォルトなし（必須指定）。"
}
