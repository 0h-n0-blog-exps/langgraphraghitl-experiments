# [DEBUG] ============================================================
# Agent   : architect
# Task    : Terraform + Docker + docker-compose 設定
# Created : 2026-02-23T18:56:02
# Updated : 2026-02-23
# [/DEBUG] ===========================================================
#
# ベースイメージ選定理由:
# - lambda ステージ: public.ecr.aws/lambda/python:3.11
#   Lambda Runtime API 組み込み。Amazon Linux 2 ベース (yum)。
#   コンテナイメージデプロイに最適。タグ固定で再現性を確保。
# - local ステージ: python:3.11-slim
#   Debian ベース (apt-get)。軽量でローカル開発に適切。
#   ネイティブビルド依存なし（requirements.txt は backend_dev が追加予定）
#   のためマルチステージビルドは不要。
# - gpu ステージ: pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime
#   CUDA 12.4 + cuDNN 9 組み込み。NVIDIA RTX 5060 Ti 対応。
#   Ollama 経由のローカル LLM 推論 (llama3.2) に使用。
#
# パッケージマネージャ確認結果 (STEP 0 B):
# - public.ecr.aws/lambda/python:3.11 → Amazon Linux 2 → yum
# - python:3.11-slim → Debian → apt-get
# - pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime → Ubuntu ベース → apt-get
#
# ネイティブビルド依存 (STEP 0 C):
# - requirements.txt は backend_dev が追加予定。C 拡張が判明次第
#   builder/runtime 分離を検討する。現時点では不要と仮定。
#

# ==========================================================================
# ---- lambda stage (for AWS deployment) -----------------------------------
# ==========================================================================
FROM public.ecr.aws/lambda/python:3.11 AS lambda

# yum: Amazon Linux 2 のパッケージマネージャ（STEP 0 B で確認済み）
# curl は healthcheck 用。Lambda 環境では通常不要だが念のため確認。
# requirements.txt に C 拡張が追加された場合は以下のコメントを外すこと:
# RUN (which yum && yum install -y gcc python3-devel && yum clean all)

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev --no-install-project

COPY src/ src/

# Lambda ハンドラー指定
CMD ["src.langgraph_rag_hitl.handler.handler"]

# ==========================================================================
# ---- local stage (for docker compose / CPU development) ------------------
# ==========================================================================
FROM python:3.11-slim AS local

WORKDIR /app

# apt-get: Debian ベース (STEP 0 B で確認済み)
# curl は healthcheck エンドポイント確認用
RUN (which apt-get && apt-get update && apt-get install -y --no-install-recommends \
      curl \
    && rm -rf /var/lib/apt/lists/*) || \
    (which apk && apk add --no-cache curl)

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev --no-install-project

COPY src/ src/

# 非 root ユーザーで実行（制約: ルートユーザーでの実行禁止）
RUN useradd --no-create-home --no-log-init app
USER app

EXPOSE 9000

# --reload なし: docker compose up -d --build で再ビルドする運用のため不要
CMD ["uvicorn", "src.langgraph_rag_hitl.server:app", "--host", "0.0.0.0", "--port", "9000"]

# ==========================================================================
# ---- gpu stage (GPU local development, HAS_GPU=true) --------------------
# ==========================================================================
FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime AS gpu

WORKDIR /app

# apt-get: Ubuntu ベース (STEP 0 B で確認済み)
# curl は healthcheck エンドポイント確認用
RUN (which apt-get && apt-get update && apt-get install -y --no-install-recommends \
      curl \
    && rm -rf /var/lib/apt/lists/*) || \
    (which apk && apk add --no-cache curl)

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev --no-install-project

COPY src/ src/

# 非 root ユーザーで実行（制約: ルートユーザーでの実行禁止）
RUN useradd --no-create-home --no-log-init app
USER app

EXPOSE 9000

# --reload なし: docker compose up -d --build で再ビルドする運用のため不要
CMD ["uvicorn", "src.langgraph_rag_hitl.server:app", "--host", "0.0.0.0", "--port", "9000"]
