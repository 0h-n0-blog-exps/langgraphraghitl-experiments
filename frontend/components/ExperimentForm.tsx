// [DEBUG] ============================================================
// Agent   : frontend_dev
// Task    : Next.js 15 フロントエンド + Playwright E2E
// Created : 2026-02-23T19:10:27
// Updated : 2026-02-23T19:10:27
// [/DEBUG] ===========================================================

"use client";

import { useState, useId } from "react";

interface ExperimentFormProps {
  onSubmit: (query: string) => void;
  isLoading: boolean;
}

export default function ExperimentForm({
  onSubmit,
  isLoading,
}: ExperimentFormProps) {
  const [query, setQuery] = useState("");
  const inputId = useId();
  const descriptionId = useId();

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
  };

  const isDisabled = isLoading || query.trim().length === 0;

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4"
      noValidate
    >
      <div className="space-y-2">
        <label
          htmlFor={inputId}
          className="block text-sm font-medium text-foreground"
        >
          検索クエリ
          <span className="text-destructive ml-1" aria-hidden="true">
            *
          </span>
        </label>
        <p id={descriptionId} className="text-sm text-muted-foreground">
          国会議事録から検索したいトピックを日本語で入力してください（例：「AI規制に関する議論」「再生可能エネルギー政策」）
        </p>
        <textarea
          id={inputId}
          data-testid="query-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="検索クエリ入力"
          aria-describedby={descriptionId}
          aria-required="true"
          required
          disabled={isLoading}
          placeholder="例: 国会での AI 規制に関する議論"
          rows={3}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-none"
        />
      </div>
      <button
        type="submit"
        data-testid="submit-button"
        disabled={isDisabled}
        aria-label={isLoading ? "送信中..." : "検索を実行"}
        className="inline-flex items-center justify-center rounded-md bg-primary px-6 py-2 text-sm font-medium text-primary-foreground ring-offset-background transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"
      >
        {isLoading ? (
          <>
            <svg
              className="mr-2 h-4 w-4 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            検索中...
          </>
        ) : (
          "検索実行"
        )}
      </button>
    </form>
  );
}
