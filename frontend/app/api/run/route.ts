// [DEBUG] ============================================================
// Agent   : frontend_dev
// Task    : Next.js 15 フロントエンド + Playwright E2E
// Created : 2026-02-23T19:10:27
// Updated : 2026-02-23T19:10:27
// [/DEBUG] ===========================================================

import { NextRequest, NextResponse } from "next/server";

const JSON_HEADERS = { "Content-Type": "application/json" };
const TIMEOUT_MS = 30_000;

export async function POST(req: NextRequest): Promise<NextResponse> {
  // API_URL 未設定チェック
  const apiUrl = process.env.API_URL;
  if (!apiUrl) {
    return NextResponse.json(
      { error: "API_URL is not configured" },
      { status: 500, headers: JSON_HEADERS }
    );
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json(
      { error: "Invalid request body" },
      { status: 400, headers: JSON_HEADERS }
    );
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

  let backendRes: Response;
  try {
    backendRes = await fetch(`${apiUrl}/api/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (err) {
    clearTimeout(timeoutId);
    const isAbort =
      err instanceof Error && err.name === "AbortError";
    if (isAbort) {
      return NextResponse.json(
        { error: "Backend timeout" },
        { status: 503, headers: JSON_HEADERS }
      );
    }
    return NextResponse.json(
      { error: "Backend unavailable" },
      { status: 503, headers: JSON_HEADERS }
    );
  } finally {
    clearTimeout(timeoutId);
  }

  let data: unknown;
  try {
    data = await backendRes.json();
  } catch {
    return NextResponse.json(
      { error: "Invalid response from backend" },
      { status: 502, headers: JSON_HEADERS }
    );
  }

  // X-Request-Id ヘッダーを転送（backend から受け取った場合）
  const responseHeaders: Record<string, string> = { ...JSON_HEADERS };
  const requestId = backendRes.headers.get("x-request-id");
  if (requestId) {
    responseHeaders["X-Request-Id"] = requestId;
  }

  return NextResponse.json(data, {
    status: backendRes.status,
    headers: responseHeaders,
  });
}
