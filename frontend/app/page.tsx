// [DEBUG] ============================================================
// Agent   : frontend_dev
// Task    : Next.js 15 フロントエンド + Playwright E2E
// Created : 2026-02-23T19:10:27
// Updated : 2026-02-23T19:10:27
// [/DEBUG] ===========================================================

"use client";

import { useState } from "react";
import ExperimentForm from "@/components/ExperimentForm";
import ResultDisplay from "@/components/ResultDisplay";

export interface ExperimentResult {
  answer: string;
  sources: Array<{
    speech_id: string;
    speaker: string;
    date: string;
    content: string;
    score: number;
    house?: string;
    meeting?: string;
  }>;
  requires_review: boolean;
  hitl_review?: {
    reason: string;
    query: string;
    relevant_doc_count: number;
    sensitive_keywords: string[];
  } | null;
  processing_time_ms: number;
  request_id: string;
  workflow_steps: string[];
}

export type PageState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: ExperimentResult }
  | { status: "error"; message: string };

export default function Home() {
  const [state, setState] = useState<PageState>({ status: "idle" });

  const handleSubmit = async (query: string) => {
    setState({ status: "loading" });

    try {
      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`;
        try {
          const errData = await response.json();
          errorMessage = errData.error ?? errorMessage;
        } catch {
          // keep default message if JSON parse fails
        }
        setState({ status: "error", message: errorMessage });
        return;
      }

      const data: ExperimentResult = await response.json();
      setState({ status: "success", data });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "予期しないエラーが発生しました";
      setState({ status: "error", message });
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <section>
        <h2 className="text-2xl font-semibold mb-2">検索クエリ入力</h2>
        <p className="text-muted-foreground mb-4">
          国会議事録から関連する答弁・発言を検索します。日本語でクエリを入力してください。
        </p>
        <ExperimentForm
          onSubmit={handleSubmit}
          isLoading={state.status === "loading"}
        />
      </section>

      <section>
        <ResultDisplay state={state} />
      </section>
    </div>
  );
}
