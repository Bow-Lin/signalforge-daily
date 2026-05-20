import { defaultConfig } from "../types/config";
import type { AppSnapshot } from "../types/bridge";

export const sampleReportMarkdown = `# SignalForge Daily Demo Report

> Demo sample. This report is bundled with the app and does not contain real user data.

## Quality Summary

| Sources scanned | Articles fetched | Candidates | Selected |
|:---:|:---:|:---:|:---:|
| 6 | 82 | 24 | 6 |

Top matched topics: agent(4), coding(3), EDA(2)

Noisy sources: Example Product Changelog

Failed sources: Example Vendor RSS

## 今日看点

今天的样例日报展示了 SignalForge Daily 的完整阅读闭环：源质量统计、推荐理由、匹配主题、原文链接和本地报告预览。真实运行时，这些内容会来自你的 RSS 信息源和 AI Provider。

## 🏆 今日必读

🥇 **Agent 编程工作流开始进入工程化阶段**

[Open source agent runtime reaches v1.0](https://example.com/agent-runtime-v1) — Local Dev Blog · 2026-05-20

> 一个开源 agent runtime 发布稳定版本，重点改善工具调用、长期任务恢复和可观察性。

💡 **Why selected**: 这类基础设施会直接影响开发者如何把 agent 从 demo 带到日常工程流程。

Matched topics: agent, coding

🏷️ agent, runtime, coding

---

🥈 **EDA 工具链开始引入更多自然语言辅助设计**

[AI-assisted EDA flow for verification planning](https://example.com/eda-verification-ai) — EDA Weekly · 2026-05-20

> 文章展示了用自然语言生成验证计划、辅助覆盖率分析和整理回归失败的 workflow。

💡 **Why selected**: 它贴近 SignalForge Daily 关注的 EDA 与 coding 交叉方向。

Matched topics: EDA, coding

🏷️ EDA, verification, workflow

---

🥉 **本地优先工具重新成为桌面效率软件的主线**

[Local-first apps and durable personal workflows](https://example.com/local-first-workflows) — Product Engineering Notes · 2026-05-20

> 讨论本地数据、可导出日志、用户控制权和离线可用性对 AI 工具的重要性。

💡 **Why selected**: 它解释了为什么日报、日志、运行记录应该留在用户自己的 workspace。

Matched topics: local-first, productivity

🏷️ local-first, desktop, privacy

---

## 数据概览

- 信息源扫描：6
- 抓取文章：82
- 入选文章：6
- 重点推荐：3
`;

const generatedAt = "2026-05-20T08:30:00+08:00";
const config = defaultConfig("Demo Workspace");

config.outputPath = "Demo Workspace/reports";
config.sources = [
  {
    id: "sample-local-dev",
    name: "Local Dev Blog",
    type: "blog",
    url: "https://example.com/local-dev/rss",
    enabled: true,
    tags: ["agent", "coding"],
    priority: "high",
    createdAt: generatedAt,
    updatedAt: generatedAt,
  },
  {
    id: "sample-eda-weekly",
    name: "EDA Weekly",
    type: "rss",
    url: "https://example.com/eda-weekly/feed.xml",
    enabled: true,
    tags: ["eda", "verification"],
    priority: "high",
    createdAt: generatedAt,
    updatedAt: generatedAt,
  },
  {
    id: "sample-product-changelog",
    name: "Example Product Changelog",
    type: "rss",
    url: "https://example.com/changelog/rss",
    enabled: true,
    tags: ["product"],
    priority: "low",
    createdAt: generatedAt,
    updatedAt: generatedAt,
  },
  {
    id: "sample-vendor-rss",
    name: "Example Vendor RSS",
    type: "rss",
    url: "https://example.com/vendor/rss",
    enabled: true,
    tags: ["vendor"],
    priority: "normal",
    createdAt: generatedAt,
    updatedAt: generatedAt,
  },
];
config.relevanceProfile = {
  interestedTopics: ["agent", "coding", "EDA"],
  mutedTopics: ["funding"],
  preferredContentTypes: ["engineering_blog", "open_source_release", "product_update"],
  language: "mixed",
};

export const sampleSnapshot: AppSnapshot = {
  config,
  runs: [
    {
      id: "demo-run-20260520",
      type: "digest",
      status: "success",
      trigger: "manual",
      startedAt: "2026-05-20T08:29:10+08:00",
      finishedAt: generatedAt,
      durationMs: 50000,
      paramsSnapshot: {
        language: "zh",
        timeRangeHours: 24,
        topN: 6,
        outputPath: "Demo Workspace/reports",
        model: "demo-sample",
      },
      stats: {
        sourcesScanned: 6,
        articlesFetched: 82,
        articlesSelected: 6,
      },
      output: {
        reportPath: "sample://demo-report",
        markdownPath: "sample://demo-report",
        logPath: "sample://demo-log",
      },
      topPicks: [
        {
          itemId: "demo-agent-runtime",
          title: "Agent 编程工作流开始进入工程化阶段",
          source: "Local Dev Blog",
          url: "https://example.com/agent-runtime-v1",
          publishedAt: generatedAt,
          reason: "这类基础设施会直接影响开发者如何把 agent 从 demo 带到日常工程流程。",
          matchedTopics: ["agent", "coding"],
          contentType: "open_source_release",
          relevanceScore: 28,
        },
        {
          itemId: "demo-eda-flow",
          title: "EDA 工具链开始引入更多自然语言辅助设计",
          source: "EDA Weekly",
          url: "https://example.com/eda-verification-ai",
          publishedAt: generatedAt,
          reason: "它贴近 SignalForge Daily 关注的 EDA 与 coding 交叉方向。",
          matchedTopics: ["EDA", "coding"],
          contentType: "engineering_blog",
          relevanceScore: 26,
        },
        {
          itemId: "demo-local-first",
          title: "本地优先工具重新成为桌面效率软件的主线",
          source: "Product Engineering Notes",
          url: "https://example.com/local-first-workflows",
          publishedAt: generatedAt,
          reason: "它解释了为什么日报、日志、运行记录应该留在用户自己的 workspace。",
          matchedTopics: ["local-first", "productivity"],
          contentType: "opinion",
          relevanceScore: 24,
        },
      ],
    },
  ],
  reports: [
    {
      id: "demo-report",
      runId: "demo-run-20260520",
      title: "SignalForge Daily Demo Report",
      generatedAt,
      language: "zh",
      markdownPath: "sample://demo-report",
      markdown: sampleReportMarkdown,
      summary: "Demo sample report for trying SignalForge Daily without an API key.",
      selectedCount: 6,
      status: "success",
    },
  ],
  sourceStats: [
    {
      runId: "demo-run-20260520",
      sourceId: "sample-local-dev",
      sourceName: "Local Dev Blog",
      sourceType: "blog",
      enabled: true,
      fetchedCount: 18,
      candidateCount: 8,
      selectedCount: 3,
      status: "success",
      startedAt: "2026-05-20T08:29:12+08:00",
      finishedAt: "2026-05-20T08:29:18+08:00",
      durationMs: 6000,
    },
    {
      runId: "demo-run-20260520",
      sourceId: "sample-eda-weekly",
      sourceName: "EDA Weekly",
      sourceType: "rss",
      enabled: true,
      fetchedCount: 14,
      candidateCount: 5,
      selectedCount: 2,
      status: "success",
      startedAt: "2026-05-20T08:29:13+08:00",
      finishedAt: "2026-05-20T08:29:17+08:00",
      durationMs: 4000,
    },
    {
      runId: "demo-run-20260520",
      sourceId: "sample-product-changelog",
      sourceName: "Example Product Changelog",
      sourceType: "rss",
      enabled: true,
      fetchedCount: 32,
      candidateCount: 2,
      selectedCount: 0,
      status: "success",
      startedAt: "2026-05-20T08:29:14+08:00",
      finishedAt: "2026-05-20T08:29:19+08:00",
      durationMs: 5000,
    },
    {
      runId: "demo-run-20260520",
      sourceId: "sample-vendor-rss",
      sourceName: "Example Vendor RSS",
      sourceType: "rss",
      enabled: true,
      fetchedCount: 0,
      candidateCount: 0,
      selectedCount: 0,
      status: "failed",
      errorType: "feed_fetch_failed",
      errorMessage: "Demo failure: feed returned HTTP 503.",
      startedAt: "2026-05-20T08:29:15+08:00",
      finishedAt: "2026-05-20T08:29:16+08:00",
      durationMs: 1000,
    },
  ],
  feedback: [],
};
