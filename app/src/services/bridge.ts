import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import type { AppConfig } from "../types/config";
import type { AppSnapshot, TestConnectionResult } from "../types/bridge";
import type { GenerateDigestEvent, RunRecord } from "../types/run";

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

export function onDigestEvent(listener: (event: GenerateDigestEvent) => void): () => void {
  let unlisten: (() => void) | null = null;
  listen<GenerateDigestEvent>("digest:event", (event) => listener(event.payload)).then((handler) => {
    unlisten = handler;
  });
  return () => unlisten?.();
}
