<!-- [DEBUG] ============================================================
Agent   : architect
Task    : Terraform + Docker + docker-compose 設定
Created : 2026-02-23T18:56:02
Updated : 2026-02-23
[/DEBUG] ============================================================ -->

# Terraform — langgraph-rag-hitl

## ⚠️ COST ALERT

このリポジトリは **OpenSearch Serverless** を使用します。

**OpenSearch Serverless の料金（2026年2月時点）:**
- OCU (OpenSearch Compute Unit): 約 $0.24/時間/OCU
- 最小構成でも **1日あたり約 $11.52 以上** が課金されます
- アイドル状態でも課金されます

**必ず実験後に `terraform destroy` を実行してください。**

```bash
cd terraform
terraform destroy \
  -var="anthropic_api_key=YOUR_KEY" \
  -var="aws_region=us-east-1"
```

Lambda と S3 は従量課金のため、アイドル時はほぼ $0 です。

---

## アーキテクチャ概要

```
[Vercel] Next.js フロント (無料 Hobby)
    ↓ API_URL (api_gateway_url output)
[API Gateway HTTP API v2]
    ↓
[Lambda] Python / LangGraph RAG HITL
    ├── [S3] 実験結果・RAG ドキュメント保存
    └── [OpenSearch Serverless] RAG ベクトルストア (VECTORSEARCH)
```

**使用サービス:**
- Lambda Container Image: `public.ecr.aws/lambda/python:3.11`
- API Gateway HTTP API (v2)
- S3 (バージョニング + SSE + パブリックアクセスブロック)
- OpenSearch Serverless (VECTORSEARCH タイプ)
- CloudWatch Logs (30日保持)

---

## 前提条件

- Terraform >= 1.5
- AWS CLI 設定済み (`aws configure`)
- ECR リポジトリにコンテナイメージがプッシュ済み
- Docker + Docker Compose v2.22+

---

## デプロイ手順

### 1. ECR リポジトリ作成 & イメージプッシュ

```bash
# ECR リポジトリ作成
aws ecr create-repository \
  --repository-name langgraph-rag-hitl \
  --region us-east-1

# Docker イメージビルド & プッシュ
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com/langgraph-rag-hitl:latest"

aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin "${AWS_ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com"

docker build --target lambda -t "${ECR_URI}" .
docker push "${ECR_URI}"
```

### 2. Terraform デプロイ

```bash
cd terraform
terraform init
terraform plan \
  -var="anthropic_api_key=YOUR_ANTHROPIC_API_KEY" \
  -var="aws_region=us-east-1" \
  -var="lambda_image_uri=${ECR_URI}" \
  -var='cors_allowed_origins=["https://your-app.vercel.app"]'

terraform apply \
  -var="anthropic_api_key=YOUR_ANTHROPIC_API_KEY" \
  -var="aws_region=us-east-1" \
  -var="lambda_image_uri=${ECR_URI}" \
  -var='cors_allowed_origins=["https://your-app.vercel.app"]'
```

### 3. API URL の確認

```bash
terraform output api_gateway_url
```

### 4. Vercel への API_URL 設定

```bash
# api_gateway_url の値を Vercel 環境変数に設定
vercel env add API_URL production
# プロンプトで terraform output api_gateway_url の値を入力
```

---

## ⚠️ 実験後の必須手順: terraform destroy

```bash
cd terraform
terraform destroy \
  -var="anthropic_api_key=YOUR_KEY" \
  -var="aws_region=us-east-1" \
  -var="lambda_image_uri=placeholder:latest"
```

**destroy 後の確認:**
```bash
# OpenSearch Serverless コレクションが削除されたか確認
aws opensearchserverless list-collections --region us-east-1

# S3 バケットが削除されたか確認
aws s3 ls | grep langgraph-rag-hitl
```

---

## ローカル開発

### コンテナ起動

```bash
docker compose build
docker compose up -d
docker compose ps
```

### Terraform 構文確認

```bash
cd terraform
terraform init -backend=false
terraform validate
terraform plan -input=false \
  -var="anthropic_api_key=dummy" \
  -var="aws_region=us-east-1" \
  -var="project_name=langgraph-rag-hitl" \
  -var='cors_allowed_origins=["*"]'
```

### 停止

```bash
docker compose down
```

---

## 環境変数

| 変数名 | ローカル開発 | 本番（AWS） | 説明 |
|---|---|---|---|
| `API_URL` | **設定不要**（docker compose が `http://backend:9000` を自動注入） | `terraform output api_gateway_url` を Vercel 環境変数に設定 | Next.js → backend の接続先 |
| `ANTHROPIC_API_KEY` | `.env` に設定（任意、ローカルモデル優先） | `terraform plan/apply` 時に `-var="anthropic_api_key=xxx"` | Anthropic API 認証キー |
| `OLLAMA_HOST` | **設定不要**（docker compose が `http://ollama:11434` を自動注入） | N/A（Lambda では使用しない） | Ollama サーバー接続先 |
| `OLLAMA_MODEL` | `.env` で設定（デフォルト: `llama3.2`） | N/A | 使用するローカル LLM モデル |

### ローカル開発での API_URL

`API_URL` は docker-compose.yml の `environment` セクションで自動設定されます:

```yaml
frontend:
  environment:
    - API_URL=http://backend:9000   # docker compose が自動注入
```

手動で `.env.local` を作成する必要はありません。

### 本番デプロイ後の API_URL 設定

```bash
cd terraform && terraform apply -var="anthropic_api_key=YOUR_KEY"
terraform output api_gateway_url   # URL を確認
vercel env add API_URL production   # URL を Vercel に設定
```

---

## Terraform 変数一覧

| 変数名 | デフォルト | 必須 | 説明 |
|---|---|---|---|
| `aws_region` | `us-east-1` | - | AWS リージョン |
| `project_name` | `langgraph-rag-hitl` | - | プロジェクト名（リソース命名に使用） |
| `anthropic_api_key` | なし | **必須** | Anthropic API キー（secrets） |
| `lambda_image_uri` | `placeholder:latest` | デプロイ時必須 | Lambda コンテナイメージ URI |
| `lambda_reserved_concurrent_executions` | `10` | - | Lambda 同時実行数上限 |
| `opensearch_data_access_principal` | `[]` | - | 追加の OpenSearch アクセス許可プリンシパル |
| `s3_force_destroy` | `true` | - | destroy 時に S3 を強制削除 |
| `log_retention_days` | `30` | - | CloudWatch ログ保持日数 |
| `cors_allowed_origins` | なし | **必須** | API Gateway CORS で許可するオリジンのリスト（例: `["https://your-app.vercel.app"]`） |
