import type { DigestLanguage } from "./config";
import type { TopPick } from "./run";

export type ReportRecord = {
  id: string;
  runId: string;
  title: string;
  generatedAt: string;
  language: DigestLanguage;
  markdownPath: string;
  summary?: string;
  topPicks?: TopPick[];
  status?: "success" | "failed";
  selectedCount?: number;
};
