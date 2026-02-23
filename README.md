<!-- [DEBUG] ============================================================
Agent   : readme_writer
Task    : README.md 生成（スキル一覧含む）
Created : 2026-02-23
Updated : 2026-02-23
[/DEBUG] ============================================================ -->

# LangGraphマルチソースRAGの本番構築：権限制御×HITLで社内検索を安全運用

## 概要

本リポジトリは、DeepRAG (arXiv:2412.10743) の手法を国会議事録コーパスで実装・検証する実験リポジトリです。

### 実装手法

- **DeepRAG (MDP-based Adaptive Retrieval)**: 複雑なクエリをサブクエリに分解し、各ステップで「外部検索」か「パラメトリック知識」かを適応的に判定するマルコフ決定過程ベースのフレームワーク
- **マルチソース RAG**: BM25（キーワード検索）と Dense ベクトル検索を Reciprocal Rank Fusion (RRF) で統合したハイブリッドリトリーバー
- **HITL (Human-In-The-Loop)**: LangGraph の条件分岐エッジ (`add_conditional_edges`) を活用した人間レビュー介入ワークフロー
- **権限制御**: ユーザーロールに応じた検索ソースフィルタリング

### 使用技術スタック

| レイヤー | 技術 |
|----------|------|
| ワークフロー | LangGraph, LangChain |
| LLM (ローカル) | Ollama (llama3.2), NVIDIA RTX 5060 Ti |
| LLM (フォールバック) | Anthropic Claude (ANTHROPIC_API_KEY) |
| バックエンド API | FastAPI, Pydantic v2, Python 3.11 |
| パッケージ管理 | uv |
| フロントエンド | Next.js 15, TypeScript (strict), Tailwind CSS, shadcn/ui |
| インフラ | AWS Lambda, API Gateway HTTP API v2, S3, OpenSearch Serverless |
| IaC | Terraform |
| テスト | pytest, Playwright E2E |
| コンテナ | Docker, docker compose (NVIDIA runtime) |

### デモ URL

Vercel (nrt1 リージョン) へのデプロイを予定 — デプロイ後にここを更新してください。

---

## アーキテクチャ

### ローカル開発環境

```
┌─────────────────────────────────────────────────────┐
│                  docker compose                       │
│                                                       │
│  ┌─────────────┐   HTTP    ┌──────────────────────┐  │
│  │  frontend   │ ────────> │  backend (FastAPI)   │  │
│  │ Next.js 15  │ :3000     │  :8000               │  │
│  └─────────────┘           │  LangGraph RAG+HITL  │  │
│                             └──────────┬───────────┘  │
│                                        │ Ollama API   │
│                             ┌──────────▼───────────┐  │
│                             │  ollama              │  │
│                             │  llama3.2 (GPU)      │  │
│                             └──────────────────────┘  │
└─────────────────────────────────────────────────────┘
         │
         │ (optional) data/corpus/
         ▼
   国会議事録 API (ndl.go.jp)  ── BM25 Index
                                ── Dense Embeddings
```

### AWS 本番環境

```
  Browser / Vercel (Next.js)
         │
         │ HTTPS
         ▼
  ┌──────────────────┐
  │  API Gateway     │  (HTTP API v2)
  │  /api/search     │
  │  /api/hitl       │
  └────────┬─────────┘
           │ invoke
           ▼
  ┌──────────────────┐       ┌──────────────────────┐
  │  AWS Lambda      │ ───>  │  OpenSearch           │
  │  (LangGraph RAG  │       │  Serverless           │
  │   HITL handler)  │       │  (ベクトル検索)       │
  └────────┬─────────┘       └──────────────────────┘
           │                  ┌──────────────────────┐
           └──────────────>   │  S3                  │
                              │  (実験結果・コーパス) │
                              └──────────────────────┘
```

### AWS リソース一覧

| リソース | 用途 |
|----------|------|
| API Gateway HTTP API v2 | REST エンドポイント公開 |
| Lambda | LangGraph RAG+HITL ハンドラ実行 |
| S3 | 国会議事録コーパス・実験結果保存 |
| OpenSearch Serverless | Dense ベクトル検索インデックス |

---

## セットアップ

### 前提条件

- Python 3.11+, [uv](https://docs.astral.sh/uv/)
- Docker + NVIDIA Container Toolkit（GPU 推論時）
- Node.js 20+, npm
- Terraform 1.9+（AWS デプロイ時）
- AWS CLI（認証済み、AWS デプロイ時）

### 0. 環境変数の設定

```bash
cp .env.example .env
# .env を編集して以下を設定:
#   OLLAMA_HOST=http://localhost:11434   # ローカル直接実行時
#   OLLAMA_MODEL=llama3.2
#   ANTHROPIC_API_KEY=sk-ant-...        # 精度不足時のフォールバック（任意）
#   HF_TOKEN=hf_...                     # HuggingFace モデル使用時（任意）
```

### 1. データ取得

```bash
uv run data/download.py   # 国会議事録 500件を data/corpus/ に取得
```

取得完了確認:

```bash
ls data/corpus/   # .json ファイルが存在すること
```

### 2. ローカル実行（Docker + Ollama）

```bash
uv sync
uv run pytest -q          # テスト実行（39テスト、API キー不要）
docker compose up -d      # ollama + backend を起動
```

GPU 有り環境では `docker compose` が NVIDIA runtime で Ollama を起動し、llama3.2 によるローカル推論を行います。

ヘルスチェック:

```bash
curl http://localhost:8000/health
```

### 3. フロントエンド

```bash
cd /home/relu/misc/zen-blog-exps/langgraphraghitl-experiments/frontend
npm install
npm run dev               # localhost:3000
npm run test:e2e          # Playwright E2E テスト
```

### 4. AWS デプロイ（課金注意）

```bash
cd /home/relu/misc/zen-blog-exps/langgraphraghitl-experiments/terraform
terraform init
terraform apply \
  -var="region=ap-northeast-1" \
  -var="project_name=langgraph-rag-hitl"
```

apply 完了後、出力された `api_gateway_url` を frontend に設定します:

```bash
# terraform output から URL を取得
API_URL=$(terraform output -raw api_gateway_url)
echo "NEXT_PUBLIC_API_URL=${API_URL}" > /home/relu/misc/zen-blog-exps/langgraphraghitl-experiments/frontend/.env.local
```

その後フロントを Vercel にデプロイ（`NEXT_PUBLIC_API_URL` 環境変数を Vercel の設定に追加）。

実験後のリソース削除（必須）:

```bash
# ⚠️ 実験後は必ず実行
terraform destroy \
  -var="region=ap-northeast-1" \
  -var="project_name=langgraph-rag-hitl"
```

---

## Claude Code スキル

`.claude/skills/` ディレクトリに登録済みのスキルは以下の通りです。

| スキル | コマンド | 説明 |
|--------|----------|------|
| setup-data | `/setup-data` | 国会議事録コーパス（500件）をダウンロードして `data/corpus/` に保存 |
| run-experiment | `/run-experiment` | 実験実行（pytest → docker compose up → 実験結果表示） |
| test-ui | `/test-ui` | Playwright E2E テストを実行して UI の不具合を検出・修正 |
| deploy-aws | `/deploy-aws` | AWS デプロイ（課金注意、`skill_generator` が生成予定） |
| destroy-aws | `/destroy-aws` | AWS リソース削除（実験後に必ず実行、`skill_generator` が生成予定） |

> `deploy-aws`, `destroy-aws` は `skill_generator` エージェント（STEP C）が `.claude/skills/` へ生成予定です。生成後にこの表を更新してください。

---

## COST ALERT

OpenSearch Serverless を使用する AWS 環境では継続的な課金が発生します。

- **OpenSearch Serverless**: 最小 2 OCU = 約 $1/時間
- **Lambda + API Gateway**: リクエスト数に応じた従量課金

**実験後は必ず以下を実行してください:**

```bash
cd /home/relu/misc/zen-blog-exps/langgraphraghitl-experiments/terraform
terraform destroy -var="region=ap-northeast-1" -var="project_name=langgraph-rag-hitl"
```

AWS コンソールで OpenSearch コレクションが削除されていることを確認してから離席してください。

---

## 参照

- **Zenn 記事**: https://zenn.dev/0h_n0/articles/e4a4b18478c692
- **1次情報記事 (DeepRAG 論文解説)**: https://0h-n0.github.io/posts/paper-2412-10743/
- **論文 (arXiv)**: https://arxiv.org/abs/2412.10743
- **国会議事録 API**: https://kokkai.ndl.go.jp/
- **LangGraph ドキュメント**: https://langchain-ai.github.io/langgraph/
