import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import type { AppConfig } from "../types/config";
import type { AppInfo, AppSnapshot, AutomationStatus, TestConnectionResult } from "../types/bridge";
import type { GenerateDigestEvent, ItemFeedback, RunRecord } from "../types/run";

export function getSnapshot(): Promise<AppSnapshot> {
  return invoke("get_snapshot");
}

export function chooseFolder(): Promise<string | null> {
  return invoke("choose_folder");
}

export function saveConfig(config: AppConfig): Promise<AppSnapshot> {
  return invoke("save_config", { config });
}

export function testConnection(config: AppConfig): Promise<TestConnectionResult> {
  return invoke("test_connection", { config });
}

export function generateDigest(): Promise<RunRecord> {
  return invoke("generate_digest");
}

export function getAutomationStatus(): Promise<AutomationStatus> {
  return invoke("get_automation_status");
}

export function setAutomationPaused(paused: boolean): Promise<AppSnapshot> {
  return invoke("set_automation_paused", { paused });
}

export function getAppInfo(): Promise<AppInfo> {
  return invoke("get_app_info");
}

export function openLogsFolder(): Promise<void> {
  return invoke("open_logs_folder");
}

export function readMarkdown(path: string): Promise<string> {
  return invoke("read_markdown", { path });
}

export function copyText(text: string): Promise<void> {
  return navigator.clipboard.writeText(text);
}

export function openPath(path: string): Promise<void> {
  return invoke("open_path", { path });
}

export function revealPath(path: string): Promise<void> {
  return invoke("reveal_path", { path });
}

export function deleteRun(runId: string): Promise<AppSnapshot> {
  return invoke("delete_run", { runId });
}

export function removeReportFromHistory(report: { runId?: string; markdownPath: string }): Promise<AppSnapshot> {
  return invoke("remove_report_from_history", { runId: report.runId || null, markdownPath: report.markdownPath });
}

export function deleteReport(report: { runId?: string; markdownPath: string }): Promise<AppSnapshot> {
  return invoke("delete_report", { runId: report.runId || null, markdownPath: report.markdownPath });
}

export function saveItemFeedback(feedback: ItemFeedback): Promise<AppSnapshot> {
  return invoke("save_item_feedback", { feedback });
}

export function onDigestEvent(listener: (event: GenerateDigestEvent) => void): () => void {
  let unlisten: (() => void) | null = null;
  listen<GenerateDigestEvent>("digest:event", (event) => listener(event.payload)).then((handler) => {
    unlisten = handler;
  });
  return () => unlisten?.();
}

export function onAppNavigate(listener: (route: string) => void): () => void {
  let unlisten: (() => void) | null = null;
  listen<string>("app:navigate", (event) => listener(event.payload)).then((handler) => {
    unlisten = handler;
  });
  return () => unlisten?.();
}

export function onAutomationChanged(listener: () => void): () => void {
  let unlisten: (() => void) | null = null;
  listen("automation:changed", () => listener()).then((handler) => {
    unlisten = handler;
  });
  return () => unlisten?.();
}

export function onAutomationNotify(listener: (payload: { title: string; body: string }) => void): () => void {
  let unlisten: (() => void) | null = null;
  listen<{ title: string; body: string }>("automation:notify", (event) => listener(event.payload)).then((handler) => {
    unlisten = handler;
  });
  return () => unlisten?.();
}
