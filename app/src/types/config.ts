export type AiProviderType = "openai_compatible" | "iflow" | "custom";
export type DigestLanguage = "zh" | "en";
export type ProxyMode = "system" | "none" | "custom";
export type SourceType = "rss" | "github" | "arxiv" | "blog" | "custom";
export type SourcePriority = "high" | "normal" | "low";
export type ContentType =
  | "engineering_blog"
  | "research_paper"
  | "open_source_release"
  | "product_update"
  | "funding_news"
  | "opinion";

export type AutomationConfig = {
  enabled: boolean;
  frequency: "daily" | "weekdays";
  timeOfDay: string;
  notifyOnSuccess: boolean;
  notifyOnFailure: boolean;
  runOnAppStartIfMissed: boolean;
  skipIfAlreadyGeneratedToday: boolean;
  pausedUntil?: string;
};

export type SourceConfig = {
  id: string;
  name: string;
  type: SourceType;
  url: string;
  enabled: boolean;
  tags: string[];
  priority: SourcePriority;
  createdAt: string;
  updatedAt: string;
};

export type RelevanceProfile = {
  interestedTopics: string[];
  mutedTopics: string[];
  preferredContentTypes: ContentType[];
  language: "zh" | "en" | "mixed";
};

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
  sources: SourceConfig[];
  relevanceProfile: RelevanceProfile;
  automation: AutomationConfig;
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
  sources: [],
  relevanceProfile: {
    interestedTopics: [],
    mutedTopics: [],
    preferredContentTypes: ["engineering_blog", "research_paper", "open_source_release", "product_update", "opinion"],
    language: "mixed",
  },
  automation: {
    enabled: false,
    frequency: "daily",
    timeOfDay: "08:30",
    notifyOnSuccess: true,
    notifyOnFailure: true,
    runOnAppStartIfMissed: true,
    skipIfAlreadyGeneratedToday: true,
    pausedUntil: undefined,
  },
});
