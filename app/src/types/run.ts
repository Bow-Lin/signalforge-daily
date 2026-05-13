import type { DigestLanguage } from "./config";

export type RunStatus = "pending" | "running" | "success" | "failed" | "cancelled";

export type DigestErrorType =
  | "missing_api_key"
  | "api_connection_failed"
  | "proxy_error"
  | "no_articles_fetched"
  | "feed_fetch_failed"
  | "model_generation_failed"
  | "write_file_failed"
  | "unknown";

export type DigestError = {
  type: DigestErrorType;
  message: string;
  raw?: string;
  suggestedActions: string[];
};

export type TopPick = {
  title: string;
  source?: string;
  url?: string;
  publishedAt?: string;
  reason?: string;
};

export type FeedFailure = {
  source: string;
  reason: string;
};

export type RunRecord = {
  id: string;
  type: "digest";
  status: RunStatus;
  startedAt: string;
  finishedAt?: string;
  durationMs?: number;
  paramsSnapshot: {
    language: DigestLanguage;
    timeRangeHours: number;
    topN: number;
    outputPath: string;
    model: string;
  };
  stats?: {
    sourcesScanned?: number;
    articlesFetched?: number;
    articlesSelected?: number;
  };
  output?: {
    reportPath?: string;
    markdownPath?: string;
    htmlPath?: string;
    jsonPath?: string;
    logPath?: string;
  };
  topPicks?: TopPick[];
  warnings?: {
    feedFailures?: FeedFailure[];
  };
  error?: DigestError;
};

export type GenerateDigestEvent =
  | { type: "started"; runId: string; record: RunRecord }
  | { type: "progress"; runId: string; step: string; message: string }
  | { type: "stats"; runId: string; sourcesScanned?: number; articlesFetched?: number; articlesSelected?: number }
  | { type: "log"; runId: string; level: "info" | "warn" | "error"; message: string }
  | { type: "completed"; runId: string; record: RunRecord }
  | { type: "failed"; runId: string; record: RunRecord };
