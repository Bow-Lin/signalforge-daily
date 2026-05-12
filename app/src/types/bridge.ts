import type { AppConfig } from "./config";
import type { GenerateDigestEvent, RunRecord } from "./run";
import type { ReportRecord } from "./report";

export type AppSnapshot = {
  config: AppConfig | null;
  runs: RunRecord[];
  reports: ReportRecord[];
};

export type TestConnectionResult = {
  ok: boolean;
  message: string;
};

export type NewsCollectionBridge = {
  getSnapshot: () => Promise<AppSnapshot>;
  chooseFolder: () => Promise<string | null>;
  saveConfig: (config: AppConfig) => Promise<AppSnapshot>;
  testConnection: (config: AppConfig) => Promise<TestConnectionResult>;
  generateDigest: () => Promise<RunRecord>;
  readMarkdown: (path: string) => Promise<string>;
  copyText: (text: string) => Promise<void>;
  openPath: (path: string) => Promise<void>;
  revealPath: (path: string) => Promise<void>;
  deleteRun: (runId: string) => Promise<AppSnapshot>;
  onDigestEvent: (listener: (event: GenerateDigestEvent) => void) => () => void;
};
