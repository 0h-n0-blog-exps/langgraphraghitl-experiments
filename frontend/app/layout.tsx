// [DEBUG] ============================================================
// Agent   : frontend_dev
// Task    : Next.js 15 フロントエンド + Playwright E2E
// Created : 2026-02-23T19:10:27
// Updated : 2026-02-23T19:10:27
// [/DEBUG] ===========================================================

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LangGraph RAG HITL - 国会議事録検索",
  description:
    "LangGraphマルチソースRAGの本番構築：権限制御×HITLで社内検索を安全運用",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body className="min-h-screen bg-background font-sans antialiased">
        <div className="min-h-screen flex flex-col">
          <header className="border-b bg-card shadow-sm">
            <div className="container mx-auto px-4 py-4">
              <h1 className="text-xl font-bold text-foreground">
                LangGraph RAG HITL — 国会議事録検索
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                権限制御 × Human-in-the-Loop によるマルチソース RAG 実験
              </p>
            </div>
          </header>
          <main className="flex-1 container mx-auto px-4 py-8">
            {children}
          </main>
          <footer className="border-t bg-muted/30 py-4">
            <div className="container mx-auto px-4 text-center text-xs text-muted-foreground">
              LangGraph RAG HITL Experiment — 国会議事録 API コーパス使用
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
