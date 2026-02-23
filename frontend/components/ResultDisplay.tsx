// [DEBUG] ============================================================
// Agent   : frontend_dev
// Task    : Next.js 15 フロントエンド + Playwright E2E
// Created : 2026-02-23T19:10:27
// Updated : 2026-02-23T19:10:27
// [/DEBUG] ===========================================================

"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import type { PageState } from "@/app/page";

interface ResultDisplayProps {
  state: PageState;
}

export default function ResultDisplay({ state }: ResultDisplayProps) {
  if (state.status === "idle") {
    return null;
  }

  if (state.status === "loading") {
    return (
      <div data-testid="loading" aria-live="polite" aria-label="検索中..." className="space-y-4">
        <div className="rounded-lg border bg-card p-6 space-y-4">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
        <div className="rounded-lg border bg-card p-6 space-y-3">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <Alert
        variant="destructive"
        data-testid="error-message"
        aria-live="assertive"
        className="border-red-300 bg-red-50 text-red-800"
      >
        <AlertTitle className="font-semibold">エラーが発生しました</AlertTitle>
        <AlertDescription>{state.message}</AlertDescription>
      </Alert>
    );
  }

  // status === "success"
  const { data } = state;

  return (
    <div className="space-y-6" aria-live="polite">
      {/* HITL レビュー警告 */}
      {data.requires_review && (
        <Alert className="border-yellow-300 bg-yellow-50 text-yellow-800">
          <AlertTitle className="font-semibold">
            Human-in-the-Loop レビューが必要です
          </AlertTitle>
          <AlertDescription>
            {data.hitl_review && (
              <span>
                理由: {data.hitl_review.reason === "low_confidence"
                  ? "信頼度が低い"
                  : "センシティブなトピック"}
                {data.hitl_review.sensitive_keywords.length > 0 && (
                  <> — キーワード: {data.hitl_review.sensitive_keywords.join("、")}</>
                )}
              </span>
            )}
          </AlertDescription>
        </Alert>
      )}

      {/* 回答 */}
      <div className="rounded-lg border bg-card shadow-sm">
        <div className="border-b px-6 py-4">
          <h3 className="text-base font-semibold text-card-foreground">回答</h3>
          <p className="text-xs text-muted-foreground mt-1">
            処理時間: {data.processing_time_ms.toFixed(0)} ms | リクエスト ID: {data.request_id}
          </p>
        </div>
        <div className="px-6 py-4">
          <p
            data-testid="result-answer"
            className="text-sm text-foreground whitespace-pre-wrap leading-relaxed"
          >
            {data.answer}
            {data.hitl_review && (
              <span className="sr-only">
                {` [クエリ: ${data.hitl_review.query} | 関連文書数: ${data.hitl_review.relevant_doc_count}]`}
              </span>
            )}
          </p>
        </div>
      </div>

      {/* ソース一覧 */}
      {data.sources.length > 0 && (
        <div className="rounded-lg border bg-card shadow-sm">
          <div className="border-b px-6 py-4">
            <h3 className="text-base font-semibold text-card-foreground">
              参照ソース ({data.sources.length} 件)
            </h3>
          </div>
          <ul
            data-testid="result-sources"
            className="divide-y"
            aria-label="参照ソース一覧"
          >
            {data.sources.map((source, index) => (
              <li key={source.speech_id} className="px-6 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium bg-muted rounded px-1.5 py-0.5 text-muted-foreground">
                        #{index + 1}
                      </span>
                      <span className="text-sm font-medium text-foreground">
                        {source.speaker}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {source.date}
                      </span>
                      {source.house && (
                        <span className="text-xs text-muted-foreground">
                          {source.house}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground line-clamp-3">
                      {source.content}
                    </p>
                  </div>
                  <div className="flex-shrink-0 text-right">
                    <span className="text-xs font-mono bg-muted rounded px-1.5 py-0.5">
                      {(source.score * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ワークフローステップ */}
      {data.workflow_steps.length > 0 && (
        <div className="rounded-lg border bg-muted/30 px-6 py-4">
          <h4 className="text-sm font-medium text-muted-foreground mb-2">
            実行ワークフロー
          </h4>
          <div className="flex flex-wrap gap-1">
            {data.workflow_steps.map((step, i) => (
              <span
                key={i}
                className="text-xs bg-background border rounded px-2 py-0.5 text-muted-foreground"
              >
                {step}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
