// [DEBUG] ============================================================
// Agent   : frontend_dev
// Task    : Next.js 15 フロントエンド + Playwright E2E
// Created : 2026-02-23T19:10:27
// Updated : 2026-02-23T19:10:27
// [/DEBUG] ===========================================================

import { cn } from "@/lib/utils";

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-muted", className)}
      {...props}
    />
  );
}

export { Skeleton };
