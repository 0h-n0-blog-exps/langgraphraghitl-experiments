# CLAUDE.md — langgraphraghitl-experiments

## 実験概要

- **タイトル**: LangGraphマルチソースRAGの本番構築：権限制御×HITLで社内検索を安全運用
- **実験タイプ**: mixed
- **Zenn 記事**: https://zenn.dev/0h_n0/articles/e4a4b18478c692
- **1次情報記事**: https://0h-n0.github.io/posts/paper-2412-10743/
- **リモートURL**: git@github.com:0h-n0-blog-exps/langgraphraghitl-experiments.git

このリポジトリは上記記事の手法を実装・検証する実験リポジトリです。
Claude Code Agent Teams が実装を担当します。

## 実行環境

- **GPU**: true (NVIDIA GeForce RTX 5060 Ti, 16311 MiB)
- **Docker NVIDIA runtime**: true
- **推奨モデル戦略**:
  - GPU 有: Ollama (llama3.2) → 外部 API (ANTHROPIC_API_KEY) の順
  - GPU 無: 外部 API 優先、またはローカル CPU モデル

## 環境変数 (.env)

実験リポジトリルートの `.env` で設定（docker-compose の env_file に含まれる）:
- `OLLAMA_HOST`: Ollama サーバー URL（docker compose 内は `http://ollama:11434`）
- `OLLAMA_MODEL`: 使用するローカルモデル（デフォルト: `llama3.2`）
- `ANTHROPIC_API_KEY`: 高精度が必要な場合のみ
- `HF_TOKEN`: HuggingFace モデルのダウンロード

## ローカル優先方針

1. **GPU 有り** → docker compose で Ollama を起動し、ローカル推論
2. **GPU 無し** → CPU で軽量モデル、または外部 API
3. **精度不足** → .env の ANTHROPIC_API_KEY を設定して外部 API へフォールバック

## 実装方針

- **データ**: 国会議事録 API（共通コーパス）で横比較可能に
- **AWS**: EC2 禁止・マネージドサービスのみ（Lambda, S3, API GW, DynamoDB, OpenSearch Serverless）
- **コスト**: OpenSearch Serverless/Bedrock 使用後は必ず `terraform destroy`
- **フロント**: Next.js 15 + TypeScript + Tailwind + shadcn/ui → Vercel (nrt1)
- **テスト**: Playwright E2E で UI 不具合ゼロを保証
- **Python**: uv + Pydantic v2 + pytest（API キー不要で全テスト通過）

## Team Lead への指示

`.claude/agents/team_lead.md` に従い、以下の順序で Teammate を spawn してください:

STEP A: **data_explorer** のみ（WebFetch で国会議事録 API 仕様確認 → data/ 生成）
  完了確認: data/sample/kokkai_sample.json が存在すること

STEP B: **architect** + **backend_dev** を並列（STEP A 完了後）
  architect → terraform/, Dockerfile, docker-compose.yml
  backend_dev → src/, tests/, pyproject.toml, .github/workflows/
  ※ backend_dev はまずこの CLAUDE.md の「1次情報記事」URL（https://0h-n0.github.io/posts/paper-2412-10743/）を WebFetch で読んで手法を理解してから実装
  完了確認: terraform/outputs.tf + pyproject.toml が両方存在すること

STEP C: **frontend_dev** + **readme_writer** + **skill_generator** を並列（STEP B 完了後）
  frontend_dev → frontend/ + e2e/ (全 Playwright テスト PASS まで修正)
  readme_writer → README.md（スキル一覧も記載）
  skill_generator → .claude/skills/{name}/SKILL.md（WebFetch で最新仕様調査）
  完了確認: frontend/e2e/*.spec.ts + README.md + .claude/skills/ に 5+ ディレクトリ

STEP D: **reviewer** + **security_reviewer** を並列（最大3回ループ）
  出力: {"verdict":"PASS"} または {"verdict":"FAIL","issues":[...]}
  指摘あり → **fix_agent** → 再レビュー / 全 PASS → 次へ

STEP E: Clean up team

## コード品質基準

- Python: 型ヒント必須, Pydantic v2, pytest で 100% テスト通過
- TypeScript: strict モード, Next.js App Router
- Terraform: terraform validate 通過, 変数に default なし（secrets）
- secrets/API キーをコードにハードコード禁止（Security で即 FAIL）

## ベストプラクティス方針

**記事の実験手法に無関係な部分**（インフラ構成・テスト設定・パッケージ管理・CI/CD 等）は、
**実装前に必ず WebSearch で最新のベストプラクティスを調査**してから実装すること。
各エージェントの担当領域で調査すべき内容は `.claude/agents/` の各定義を参照。
