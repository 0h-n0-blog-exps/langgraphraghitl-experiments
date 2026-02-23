// [DEBUG] ============================================================
// Agent   : frontend_dev
// Task    : Next.js 15 フロントエンド + Playwright E2E
// Created : 2026-02-23T19:10:27
// Updated : 2026-02-23T19:10:27
// [/DEBUG] ===========================================================

import { test, expect } from "@playwright/test";

const TEST_QUERIES = [
  { input: "国会での AI 規制に関する議論", expectField: "answer" },
  { input: "再生可能エネルギー政策", expectField: "sources" },
];

// --------------------------------------------------------------------
// 1. ページが正常に表示される
// --------------------------------------------------------------------
test("1. ページが正常に表示される (title/heading 確認)", async ({ page }) => {
  await page.goto("/");

  // title タグ確認
  await expect(page).toHaveTitle(/LangGraph RAG HITL/i);

  // h1 heading 確認
  const heading = page.locator("h1");
  await expect(heading).toBeVisible();
  await expect(heading).toContainText("LangGraph RAG HITL");

  // ExperimentForm が表示されていること
  await expect(page.locator('[data-testid="query-input"]')).toBeVisible();
  await expect(page.locator('[data-testid="submit-button"]')).toBeVisible();
});

// --------------------------------------------------------------------
// 2. ExperimentForm にデータを入力して Submit できる
// --------------------------------------------------------------------
test("2. ExperimentForm にデータを入力して Submit できる", async ({ page }) => {
  await page.goto("/");

  // 初期状態: submit ボタンが disabled（空欄）
  const submitButton = page.locator('[data-testid="submit-button"]');
  await expect(submitButton).toBeDisabled();

  // テキストを入力
  const input = page.locator('[data-testid="query-input"]');
  await input.fill("テスト入力: AI規制");

  // 入力後は submit ボタンが有効
  await expect(submitButton).toBeEnabled();

  // フォームを submit（API 応答を待たずに loading 状態を確認するため）
  await submitButton.click();

  // ローディングか結果のいずれかが表示されること（API が接続できないケースも考慮）
  const hasLoadingOrResult = await Promise.race([
    page
      .locator('[data-testid="loading"]')
      .waitFor({ state: "visible", timeout: 5_000 })
      .then(() => true)
      .catch(() => false),
    page
      .locator('[data-testid="result-answer"]')
      .waitFor({ state: "visible", timeout: 5_000 })
      .then(() => true)
      .catch(() => false),
    page
      .locator('[data-testid="error-message"]')
      .waitFor({ state: "visible", timeout: 5_000 })
      .then(() => true)
      .catch(() => false),
  ]);
  expect(hasLoadingOrResult).toBe(true);
});

// --------------------------------------------------------------------
// 3. ResultDisplay が実 API の応答を表示する
// --------------------------------------------------------------------
test("3. ResultDisplay が実 API の応答を表示する", async ({ page }) => {
  await page.goto("/");
  await page.fill('[data-testid="query-input"]', TEST_QUERIES[0].input);
  await page.click('[data-testid="submit-button"]');

  // ローディング状態が表示される
  await expect(page.locator('[data-testid="loading"]')).toBeVisible();

  // 結果が表示される（最大 30 秒 — LLM 推論時間を考慮）
  await expect(page.locator('[data-testid="result-answer"]')).toBeVisible({
    timeout: 30_000,
  });

  const answer = await page.locator('[data-testid="result-answer"]').textContent();
  expect(answer).toBeTruthy();
  expect(answer!.length).toBeGreaterThan(10); // 空・ダミー禁止
});

// --------------------------------------------------------------------
// 3b. 複数クエリで結果が異なることを確認（固定値モックでないことの証明）
// --------------------------------------------------------------------
test("3b. 複数クエリで結果が異なることを確認（実装の証明）", async ({ page }) => {
  const results: string[] = [];

  for (const q of TEST_QUERIES) {
    await page.goto("/");
    await page.fill('[data-testid="query-input"]', q.input);
    await page.click('[data-testid="submit-button"]');

    await expect(page.locator('[data-testid="result-answer"]')).toBeVisible({
      timeout: 30_000,
    });

    const text = await page.locator('[data-testid="result-answer"]').textContent();
    results.push(text ?? "");
  }

  // 異なる入力 → 異なる応答
  expect(results[0]).not.toBe(results[1]);
  expect(results[0].length).toBeGreaterThan(10);
  expect(results[1].length).toBeGreaterThan(10);
});

// --------------------------------------------------------------------
// 4. エラー時にエラーメッセージが表示される
// --------------------------------------------------------------------
test("4. エラー時にエラーメッセージが表示される", async ({ page }) => {
  // API ルートをインターセプトしてエラーを返す
  await page.route("/api/run", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ error: "Backend unavailable (test)" }),
    });
  });

  await page.goto("/");
  await page.fill('[data-testid="query-input"]', "エラーテスト用クエリ");
  await page.click('[data-testid="submit-button"]');

  // エラーメッセージが表示される
  await expect(page.locator('[data-testid="error-message"]')).toBeVisible({
    timeout: 10_000,
  });
  const errorText = await page
    .locator('[data-testid="error-message"]')
    .textContent();
  expect(errorText).toBeTruthy();
  expect(errorText!.length).toBeGreaterThan(0);
});

// --------------------------------------------------------------------
// 5. ローディング状態が表示される
// --------------------------------------------------------------------
test("5. ローディング状態が表示される", async ({ page }) => {
  // API ルートを遅延させてローディング状態を確認
  await page.route("/api/run", async (route) => {
    // 1 秒遅延してから正常レスポンスを返す
    await new Promise((resolve) => setTimeout(resolve, 1_000));
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        answer: "テスト回答: ローディング確認用",
        sources: [],
        requires_review: false,
        hitl_review: null,
        processing_time_ms: 100,
        request_id: "test-loading-id",
        workflow_steps: ["retrieve", "grade", "generate"],
      }),
    });
  });

  await page.goto("/");
  await page.fill('[data-testid="query-input"]', "ローディングテスト用クエリ");
  await page.click('[data-testid="submit-button"]');

  // ローディング Skeleton が表示される
  await expect(page.locator('[data-testid="loading"]')).toBeVisible({
    timeout: 5_000,
  });

  // 送信中はボタンが disabled になる
  await expect(page.locator('[data-testid="submit-button"]')).toBeDisabled();

  // 最終的に結果が表示される
  await expect(page.locator('[data-testid="result-answer"]')).toBeVisible({
    timeout: 10_000,
  });
});
