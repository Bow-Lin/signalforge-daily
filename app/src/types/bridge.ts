import type { AppConfig } from "./config";
import type { GenerateDigestEvent, ItemFeedback, RunRecord, SourceRunStat } from "./run";
import type { ReportRecord } from "./report";

export type AppSnapshot = {
  config: AppConfig | null;
  runs: RunRecord[];
  reports: ReportRecord[];
  sourceStats: SourceRunStat[];
  feedback: ItemFeedback[];
};

export type TestConnectionResult = {
  ok: boolean;
  message: string;
};

export type AutomationStatus = {
  enabled: boolean;
  paused: boolean;
  nextRunAt?: string;
  lastAutomationRun?: RunRecord;
  lastSkipReason?: string;
};

export type AppInfo = {
  appName: string;
  version: string;
  buildDate: string;
  platform: string;
  workspacePath?: string;
  repositoryUrl: string;
  logsPath?: string;
};

export type NewsCollectionBridge = {
  getSnapshot: () => Promise<AppSnapshot>;
  chooseFolder: () => Promise<string | null>;
  saveConfig: (config: AppConfig) => Promise<AppSnapshot>;
  testConnection: (config: AppConfig) => Promise<TestConnectionResult>;
  generateDigest: () => Promise<RunRecord>;
  getAutomationStatus: () => Promise<AutomationStatus>;
  setAutomationPaused: (paused: boolean) => Promise<AppSnapshot>;
  getAppInfo: () => Promise<AppInfo>;
  openLogsFolder: () => Promise<void>;
  readMarkdown: (path: string) => Promise<string>;
  copyText: (text: string) => Promise<void>;
  openPath: (path: string) => Promise<void>;
  revealPath: (path: string) => Promise<void>;
  deleteRun: (runId: string) => Promise<AppSnapshot>;
  removeReportFromHistory: (report: { runId?: string; markdownPath: string }) => Promise<AppSnapshot>;
  restoreReportToHistory: (report: { markdownPath: string }) => Promise<AppSnapshot>;
  deleteReport: (report: { runId?: string; markdownPath: string }) => Promise<AppSnapshot>;
  saveItemFeedback: (feedback: ItemFeedback) => Promise<AppSnapshot>;
  deleteItemFeedback: (itemId: string, reportId: string) => Promise<AppSnapshot>;
  onDigestEvent: (listener: (event: GenerateDigestEvent) => void) => () => void;
};
