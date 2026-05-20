import type { AppConfig } from "../types/config";

export type ConfigReadiness = {
  ready: boolean;
  missing: string[];
};

export function getConfigReadiness(config: AppConfig | null): ConfigReadiness {
  if (!config) {
    return { ready: false, missing: ["workspacePath", "outputPath", "apiKey", "model"] };
  }

  const missing: string[] = [];
  if (!config.workspacePath.trim()) missing.push("workspacePath");
  if (!config.outputPath.trim()) missing.push("outputPath");
  if (!config.aiProvider.apiKey.trim()) missing.push("apiKey");
  if (!config.aiProvider.model.trim()) missing.push("model");

  return {
    ready: missing.length === 0,
    missing,
  };
}
