# [DEBUG] ============================================================
# Agent   : architect
# Task    : Terraform + Docker + docker-compose 設定
# Created : 2026-02-23T18:56:02
# Updated : 2026-02-23
# [/DEBUG] ===========================================================

# ---------------------------------------------------------------------------
# データソース
# ---------------------------------------------------------------------------

# S3 バケット名のユニーク化に使用するランダムサフィックス
# （aws_caller_identity の STS 呼び出しを回避し、ローカル検証を可能にする）
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# ---------------------------------------------------------------------------
# S3: 実験結果・RAG ドキュメント保存バケット
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "experiments" {
  bucket        = "${var.project_name}-experiments-${random_id.bucket_suffix.hex}"
  force_destroy = var.s3_force_destroy

  tags = {
    Name = "${var.project_name}-experiments"
  }
}

resource "aws_s3_bucket_versioning" "experiments" {
  bucket = aws_s3_bucket.experiments.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "experiments" {
  bucket = aws_s3_bucket.experiments.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "experiments" {
  bucket = aws_s3_bucket.experiments.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------------------------------------------------------------------------
# IAM: Lambda 実行ロール
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${var.project_name}-lambda-exec"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = {
    Name = "${var.project_name}-lambda-exec"
  }
}

# Lambda 基本実行ポリシー（CloudWatch Logs への書き込み権限）
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# S3 アクセスポリシー（最小権限: 実験バケットのみ）
data "aws_iam_policy_document" "lambda_s3" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.experiments.arn,
      "${aws_s3_bucket.experiments.arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "lambda_s3" {
  name   = "${var.project_name}-lambda-s3"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_s3.json
}

# OpenSearch Serverless アクセスポリシー（RAG 検索用）
data "aws_iam_policy_document" "lambda_opensearch" {
  statement {
    effect = "Allow"
    actions = [
      "aoss:APIAccessAll",
    ]
    resources = [
      aws_opensearchserverless_collection.rag.arn,
    ]
  }
}

resource "aws_iam_role_policy" "lambda_opensearch" {
  name   = "${var.project_name}-lambda-opensearch"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_opensearch.json
}

# ---------------------------------------------------------------------------
# OpenSearch Serverless: RAG ベクトルストア
# ---------------------------------------------------------------------------

# 暗号化ポリシー
resource "aws_opensearchserverless_security_policy" "encryption" {
  name        = "${var.project_name}-enc"
  type        = "encryption"
  description = "Default encryption policy for ${var.project_name} RAG collection"

  policy = jsonencode({
    Rules = [
      {
        ResourceType = "collection"
        Resource     = ["collection/${var.project_name}-rag"]
      }
    ]
    AWSOwnedKey = true
  })
}

# ネットワークポリシー（パブリックアクセス — 実験用。本番では VPC エンドポイントに変更）
resource "aws_opensearchserverless_security_policy" "network" {
  name        = "${var.project_name}-net"
  type        = "network"
  description = "Network policy for ${var.project_name} RAG collection"

  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource     = ["collection/${var.project_name}-rag"]
        },
        {
          ResourceType = "dashboard"
          Resource     = ["collection/${var.project_name}-rag"]
        }
      ]
      AllowFromPublic = true
    }
  ])
}

# データアクセスポリシー（Lambda ロール + オプションの追加プリンシパル）
resource "aws_opensearchserverless_access_policy" "data" {
  name        = "${var.project_name}-data"
  type        = "data"
  description = "Data access policy for ${var.project_name} RAG collection"

  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "index"
          Resource     = ["index/${var.project_name}-rag/*"]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument",
          ]
        },
        {
          ResourceType = "collection"
          Resource     = ["collection/${var.project_name}-rag"]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems",
          ]
        }
      ]
      Principal = concat(
        [aws_iam_role.lambda_exec.arn],
        var.opensearch_data_access_principal
      )
    }
  ])
}

# RAG コレクション（VECTORSEARCH タイプ）
resource "aws_opensearchserverless_collection" "rag" {
  name        = "${var.project_name}-rag"
  type        = "VECTORSEARCH"
  description = "RAG vector store for ${var.project_name}"

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network,
  ]

  tags = {
    Name = "${var.project_name}-rag"
  }
}

# ---------------------------------------------------------------------------
# CloudWatch Logs: Lambda ログ保持設定
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-lambda-logs"
  }
}

# ---------------------------------------------------------------------------
# Lambda: コンテナイメージ関数
# ---------------------------------------------------------------------------

resource "aws_lambda_function" "api" {
  function_name = var.project_name
  role          = aws_iam_role.lambda_exec.arn

  # コンテナイメージデプロイ
  package_type = "Image"
  image_uri    = var.lambda_image_uri

  # パフォーマンス設定
  timeout      = 30
  memory_size  = 1024

  # コスト保護: 同時実行数の上限（-1 は禁止）
  reserved_concurrent_executions = var.lambda_reserved_concurrent_executions

  environment {
    variables = {
      ANTHROPIC_API_KEY         = var.anthropic_api_key
      S3_BUCKET                 = aws_s3_bucket.experiments.id
      OPENSEARCH_ENDPOINT       = aws_opensearchserverless_collection.rag.collection_endpoint
      OPENSEARCH_COLLECTION_ARN = aws_opensearchserverless_collection.rag.arn
      PROJECT_NAME              = var.project_name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy_attachment.lambda_basic,
  ]

  tags = {
    Name = "${var.project_name}-api"
  }
}

# ---------------------------------------------------------------------------
# API Gateway HTTP API (v2)
# ---------------------------------------------------------------------------

resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"
  description   = "HTTP API Gateway for ${var.project_name}"

  cors_configuration {
    allow_headers = ["content-type", "authorization"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    # 本番では cors_allowed_origins 変数に具体的なオリジン URL を指定すること
    allow_origins = var.cors_allowed_origins
  }

  tags = {
    Name = "${var.project_name}-api-gateway"
  }
}

# Lambda 統合
resource "aws_apigatewayv2_integration" "lambda" {
  api_id             = aws_apigatewayv2_api.main.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

# デフォルトルート（全パス・全メソッドを Lambda に転送）
resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# デフォルトステージ（自動デプロイ有効）
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      sourceIp       = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }

  tags = {
    Name = "${var.project_name}-api-stage"
  }
}

# API Gateway ログ
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.project_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name = "${var.project_name}-api-gateway-logs"
  }
}

# Lambda 呼び出し許可（API Gateway から）
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}
