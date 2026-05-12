export type AiProviderType = "openai_compatible" | "iflow" | "custom";
export type DigestLanguage = "zh" | "en";
export type ProxyMode = "system" | "none" | "custom";

export type AppConfig = {
  workspacePath: string;
  outputPath: string;
  aiProvider: {
    provider: AiProviderType;
    apiKey: string;
    baseUrl?: string;
    model: string;
  };
  digestDefaults: {
    language: DigestLanguage;
    timeRangeHours: number;
    topN: number;
  };
  network: {
    proxyMode: ProxyMode;
    httpProxy?: string;
    httpsProxy?: string;
  };
  advanced: {
    feedConcurrency?: number;
    aiRetries?: number;
    maxAiArticles?: number;
  };
};

export const defaultConfig = (workspacePath = ""): AppConfig => ({
  workspacePath,
  outputPath: workspacePath ? `${workspacePath}/reports` : "",
  aiProvider: {
    provider: "iflow",
    apiKey: "",
    baseUrl: "",
    model: "qwen3-max",
  },
  digestDefaults: {
    language: "zh",
    timeRangeHours: 24,
    topN: 15,
  },
  network: {
    proxyMode: "system",
    httpProxy: "",
    httpsProxy: "",
  },
  advanced: {
    feedConcurrency: 10,
    aiRetries: 1,
    maxAiArticles: 120,
  },
});
