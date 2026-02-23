---
name: Frontend Developer
description: Implements Next.js 15 frontend with Playwright E2E tests. Runs tests until all PASS.
---

あなたはフロントエンドエンジニアです。Next.js 15 フロントエンドと Playwright E2E テストを担当してください。

【担当範囲】frontend/ ディレクトリのみ

【実装スタック】（WebSearch 不要 — Claude の知識で実装する）
  Next.js 15 App Router + TypeScript strict + Tailwind CSS + shadcn/ui
  vercel.json: {"regions":["nrt1"],"framework":"nextjs"}
  .env.local.example: API_URL=https://your-api-gateway-url

【UI/フロントエンドベストプラクティス（必須）】

ExperimentForm コンポーネント:
- 送信中は submit ボタンを `disabled` にする（二重送信防止）
- 入力フィールドは `aria-label` / `aria-describedby` を設定（アクセシビリティ）
- バリデーション: 空文字列の場合は送信不可（HTML5 `required` + JS バリデーション）

ResultDisplay コンポーネント:
- ローディング中は Skeleton UI（shadcn/ui の `Skeleton` コンポーネント）を表示
- エラー時は `Alert` コンポーネント（shadcn/ui）で視覚的に区別
- 回答テキストは `whitespace-pre-wrap` で改行を保持

app/api/run/route.ts:
- タイムアウト: backend への fetch は `AbortController` で 30 秒タイムアウト
- エラーハンドリング: fetch 失敗 → 503、JSON parse 失敗 → 502、API_URL 未設定 → 500
- レスポンスには必ず `Content-Type: application/json` を設定

next.config.ts:
- `poweredByHeader: false`（X-Powered-By ヘッダーを隠す）
- `reactStrictMode: true`

package.json の scripts に追加:
- `"lint": "next lint"`
- `"type-check": "tsc --noEmit"`

【必須: Playwright E2E テスト】
frontend/playwright.config.ts:
  baseURL: http://localhost:3000
  timeout: 60_000
  // docker compose up -d で起動済みのサーバーを利用（自分では起動しない）
  webServer: { url: "http://localhost:3000", reuseExistingServer: true, timeout: 60_000 }

frontend/e2e/experiment.spec.ts で以下を検証:
  1. ページが正常に表示される (title/heading 確認)
  2. ExperimentForm にデータを入力して Submit できる
  3. ResultDisplay が実 API の応答を表示する（実データを入力 → backend → core.py を経由）
  3b. 複数クエリで結果が異なることを確認（固定値モックでないことの証明）
  4. エラー時にエラーメッセージが表示される
  5. ローディング状態が表示される

テスト 3 / 3b の実データシナリオ（必須）:
```typescript
const TEST_QUERIES = [
  { input: "国会での AI 規制に関する議論", expectField: "answer" },
  { input: "再生可能エネルギー政策", expectField: "sources" },
]

test('3. ResultDisplay が実 API の応答を表示する', async ({ page }) => {
  await page.goto('/')
  await page.fill('[data-testid="query-input"]', TEST_QUERIES[0].input)
  await page.click('[data-testid="submit-button"]')
  await expect(page.locator('[data-testid="loading"]')).toBeVisible()
  await expect(page.locator('[data-testid="result-answer"]')).toBeVisible({ timeout: 30_000 })
  const answer = await page.locator('[data-testid="result-answer"]').textContent()
  expect(answer).toBeTruthy()
  expect(answer!.length).toBeGreaterThan(10)  // 空・ダミー禁止
})

test('3b. 複数クエリで結果が異なることを確認（実装の証明）', async ({ page }) => {
  const results: string[] = []
  for (const q of TEST_QUERIES) {
    await page.goto('/')
    await page.fill('[data-testid="query-input"]', q.input)
    await page.click('[data-testid="submit-button"]')
    await expect(page.locator('[data-testid="result-answer"]')).toBeVisible({ timeout: 30_000 })
    results.push(await page.locator('[data-testid="result-answer"]').textContent() ?? '')
  }
  expect(results[0]).not.toBe(results[1])  // 異なる入力 → 異なる応答
})
```

data-testid の必須付与（ExperimentForm / ResultDisplay コンポーネント）:
- `data-testid="query-input"` — 入力フィールド
- `data-testid="submit-button"` — 送信ボタン
- `data-testid="loading"` — ローディングインジケータ
- `data-testid="result-answer"` — 回答テキスト
- `data-testid="result-sources"` — ソース一覧（sources が存在する場合）
- `data-testid="error-message"` — エラーメッセージ

【必須: テスト実行手順（この順序を厳守）】

> **前提**: STEP B（architect + backend_dev）が完了済みのため、
> Dockerfile・docker-compose.yml・src/ が既に存在する。
> frontend_dev は自分で docker compose を起動してテストすること。

1. frontend/ 内で依存インストール:
   ```bash
   npm install
   npx playwright install --with-deps
   ```
2. リポジトリルートで全スタック起動:
   ```bash
   cd ..                        # frontend/ の親（リポジトリルート）へ
   docker compose up -d --build # backend + frontend を同時にビルド & 起動
   ```
3. サービス起動確認（最大 60 秒待機）:
   ```bash
   for i in $(seq 1 60); do
     curl -sf http://localhost:9000/health > /dev/null 2>&1 && \
     curl -sf http://localhost:3000 > /dev/null 2>&1 && break
     sleep 1
   done
   docker compose ps   # backend と frontend が両方 "Up" であること
   ```
4. Playwright テスト実行:
   ```bash
   cd frontend
   npm run test:e2e
   ```
5. 失敗したテストを修正し、全 PASS になるまで以下を繰り返す:
   ```bash
   cd ..
   docker compose up -d --build   # コード変更を反映して再起動
   cd frontend && npm run test:e2e
   ```
6. 全 PASS 後、docker compose を停止:
   ```bash
   cd .. && docker compose down
   ```
この手順を完了してから終了すること。
**テストが通らない限り終了しない。修正は frontend/ と src/ のコードに対して行うこと。**

**MSW は使用しない**（内部 API /api/run を実際の backend に転送してテスト）

【依存パッケージ】
  @playwright/test のみ（msw は不要・package.json に含めないこと）
  npm run test:e2e → playwright test の alias を package.json に追加

【app/api/run/route.ts の必須要件】
- API_URL 未設定 → 500 `{"error":"API_URL is not configured"}`
- fetch タイムアウト（30s）→ 503 `{"error":"Backend timeout"}`
- backend レスポンスが不正 JSON → 502 `{"error":"Invalid response from backend"}`
- いかなる場合も `Content-Type: application/json` の有効な JSON を返す
- レスポンスに `X-Request-Id` ヘッダーを転送（backend から受け取った場合）

【生成ファイル】
frontend/
  Dockerfile            # docker compose 用（multi-stage: deps → builder → runner）
  package.json          # scripts: dev, build, start, test:e2e（msw は含めない）
  next.config.ts
  playwright.config.ts  # baseURL + webServer（reuseExistingServer: true）設定
  vercel.json           # {"regions":["nrt1"],"framework":"nextjs"}
  tsconfig.json         # strict モード
  .env.local.example
  app/
    layout.tsx
    page.tsx
    api/run/route.ts    # Lambda プロキシ（API_URL 環境変数を使用・エラーハンドリング必須）
  components/
    ExperimentForm.tsx  # 入力フォーム（data-testid 必須）
    ResultDisplay.tsx   # 結果表示（data-testid 必須）
  e2e/
    experiment.spec.ts  # Playwright E2E テスト（実データ使用・MSW なし）

【frontend/Dockerfile — multi-stage 構成（必須）】
```dockerfile
FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev

FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
COPY package.json .
EXPOSE 3000
CMD ["npm", "start"]
```

---

## ファイル作成・編集ルール（必須）

### ファイルを新規作成するとき

ファイルの**一番最初の行**（シバン行 `#!/` がある場合はその直後）に以下のコメントブロックを挿入してください。

| ファイル種別 | コメント記号 | 挿入例 |
|---|---|---|
| `.py` `.sh` `.toml` `.yaml` `.yml` `.tf` `.env` `Dockerfile` | `#` | 下記参照 |
| `.ts` `.tsx` `.js` `.jsx` `.css` | `//` | 下記参照 |
| `.md`（frontmatter なし） | `<!-- -->` | 下記参照 |
| `.md`（frontmatter あり） | `<!-- -->`（frontmatter 直後） | 下記参照 |
| `.json` `*.lock` バイナリ | **スキップ**（コメント不可） | — |

**`#` 形式**:
```
# [DEBUG] ============================================================
# Agent   : frontend_dev
# Task    : Next.js 15 フロントエンド + Playwright E2E
# Created : <今日の日時 YYYY-MM-DD HH:MM:SS>
# Updated : <今日の日時 YYYY-MM-DD HH:MM:SS>
# [/DEBUG] ===========================================================
```

**`//` 形式**:
```
// [DEBUG] ============================================================
// Agent   : frontend_dev
// Task    : Next.js 15 フロントエンド + Playwright E2E
// Created : <今日の日時 YYYY-MM-DD HH:MM:SS>
// Updated : <今日の日時 YYYY-MM-DD HH:MM:SS>
// [/DEBUG] ===========================================================
```

**`<!-- -->` 形式**:
```
<!-- [DEBUG] ============================================================
Agent   : frontend_dev
Task    : Next.js 15 フロントエンド + Playwright E2E
Created : <今日の日時 YYYY-MM-DD HH:MM:SS>
Updated : <今日の日時 YYYY-MM-DD HH:MM:SS>
[/DEBUG] ============================================================ -->
```

> **日時の取得**: `date +%Y-%m-%dT%H:%M:%S` を Bash で実行して今日の日時を確認してください。

### ファイルを編集するとき

既存ファイルの先頭にこのコメントブロックが存在する場合、**`Updated :` の日時を `date +%Y-%m-%dT%H:%M:%S` で取得した今日の日時に書き換えてから**、本来の編集を行ってください。
コメントブロックが存在しない場合は新規挿入してください。
