import { useEffect, useRef, useState } from "react";
import { saveConfig } from "../services/bridge";
import { formatDateTime } from "../services/format";
import type { AppSnapshot } from "../types/bridge";
import type { AppConfig, SourceConfig, SourcePriority, SourceType } from "../types/config";
import type { SourceRunStat } from "../types/run";
import { EmptyState, PageHeader, StatusBadge, type ToastItem } from "../components/ui";

type Props = {
  config: AppConfig;
  sourceStats: SourceRunStat[];
  onSnapshot: (snapshot: AppSnapshot) => void;
  demoMode?: boolean;
  searchFocusNonce?: number;
  onToast: (toast: Omit<ToastItem, "id">) => string;
};

type SourceHealth = {
  latest?: SourceRunStat;
  recentFailures: number;
  noisy: boolean;
  selectedRate: number;
};

type NewSourceDraft = {
  name: string;
  type: SourceType;
  url: string;
  tags: string;
  priority: SourcePriority;
};

const emptyDraft = (): NewSourceDraft => ({
  name: "",
  type: "rss",
  url: "",
  tags: "",
  priority: "normal",
});

export function SourcesPage({ config, sourceStats, onSnapshot, demoMode = false, searchFocusNonce = 0, onToast }: Props) {
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState<NewSourceDraft>(emptyDraft);
  const [formError, setFormError] = useState("");
  const [query, setQuery] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);
  const sourceHealth = new Map(config.sources.map((source) => [source.id, getSourceHealth(source, sourceStats)]));
  const enabledCount = config.sources.filter((source) => source.enabled).length;
  const noisySources = config.sources.filter((source) => sourceHealth.get(source.id)?.noisy);
  const failedSources = config.sources.filter((source) => (sourceHealth.get(source.id)?.recentFailures || 0) > 0);
  const healthyCount = config.sources.filter((source) => {
    const health = sourceHealth.get(source.id);
    return source.enabled && health?.latest?.status === "success" && !health.noisy;
  }).length;
  const visibleSources = config.sources.filter((source) => matchesSourceQuery(source, query));

  useEffect(() => {
    if (searchFocusNonce > 0) searchRef.current?.focus();
  }, [searchFocusNonce]);

  const toggleSource = async (source: SourceConfig) => {
    if (demoMode) return;
    const previousConfig = config;
    const now = new Date().toISOString();
    const next = await saveConfig({
      ...config,
      sources: config.sources.map((item) =>
        item.id === source.id ? { ...item, enabled: !item.enabled, updatedAt: now } : item,
      ),
    });
    onSnapshot(next);
    onToast({
      title: source.enabled ? "已禁用信息源" : "已启用信息源",
      description: source.name,
      actionLabel: "撤销",
      onAction: async () => {
        const restored = await saveConfig(previousConfig);
        onSnapshot(restored);
      },
    });
  };

  const addSource = async () => {
    if (demoMode) {
      setFormError("Demo Mode 不会保存真实信息源。清除 Demo 后可添加自己的 RSS。");
      return;
    }
    const name = draft.name.trim();
    const url = draft.url.trim();
    if (!name || !url) {
      setFormError("请填写名称和 URL。");
      return;
    }
    if (!isLikelyUrl(url)) {
      setFormError("请输入有效的 URL，例如 https://example.com/feed.xml。");
      return;
    }
    if (config.sources.some((source) => normalizeUrl(source.url) === normalizeUrl(url))) {
      setFormError("这个信息源已经存在。");
      return;
    }
    const previousConfig = config;
    const now = new Date().toISOString();
    const next = await saveConfig({
      ...config,
      sources: [
        {
          id: createSourceId(url),
          name,
          type: draft.type,
          url,
          enabled: true,
          tags: splitTags(draft.tags),
          priority: draft.priority,
          createdAt: now,
          updatedAt: now,
        },
        ...config.sources,
      ],
    });
    onSnapshot(next);
    setDraft(emptyDraft());
    setFormError("");
    setAdding(false);
    onToast({
      title: "已保存信息源",
      description: name,
      actionLabel: "撤销",
      onAction: async () => {
        const restored = await saveConfig(previousConfig);
        onSnapshot(restored);
      },
    });
  };

  return (
    <div className="page sources-page">
      <PageHeader
        eyebrow="SOURCES"
        title="Source Quality & Trust"
        description="控制日报的信息源质量，观察每个源最近的抓取、入选和失败情况。"
        actions={
          <button className="primary-action source-add-button" disabled={demoMode} onClick={() => setAdding((value) => !value)}>
            {adding ? "收起" : "新增信息源"}
          </button>
        }
      />

      {adding && (
        <section className="panel add-source-panel">
          <div className="panel-header">
            <div>
              <h2>新增信息源</h2>
              <p className="muted">添加 RSS、博客或自定义源后，下一次生成日报会自动纳入抓取。</p>
            </div>
          </div>
          <div className="add-source-grid">
            <label>
              名称
              <input
                value={draft.name}
                placeholder="例如 OpenAI Blog"
                onChange={(event) => {
                  setFormError("");
                  setDraft((current) => ({ ...current, name: event.target.value }));
                }}
              />
            </label>
            <label>
              类型
              <select value={draft.type} onChange={(event) => setDraft((current) => ({ ...current, type: event.target.value as SourceType }))}>
                <option value="rss">RSS</option>
                <option value="github">GitHub</option>
                <option value="arxiv">arXiv</option>
                <option value="blog">博客</option>
                <option value="custom">自定义</option>
              </select>
            </label>
            <label className="wide-field">
              URL
              <input
                value={draft.url}
                placeholder="https://example.com/feed.xml"
                onChange={(event) => {
                  setFormError("");
                  setDraft((current) => ({ ...current, url: event.target.value }));
                }}
              />
            </label>
            <label>
              标签
              <input
                value={draft.tags}
                placeholder="agent, coding"
                onChange={(event) => setDraft((current) => ({ ...current, tags: event.target.value }))}
              />
            </label>
            <label>
              优先级
              <select value={draft.priority} onChange={(event) => setDraft((current) => ({ ...current, priority: event.target.value as SourcePriority }))}>
                <option value="high">高</option>
                <option value="normal">普通</option>
                <option value="low">低</option>
              </select>
            </label>
          </div>
          {formError && <p className="soft-error">{formError}</p>}
          <div className="actions">
            <button onClick={addSource}>保存信息源</button>
            <button
              className="secondary"
              onClick={() => {
                setDraft(emptyDraft());
                setFormError("");
                setAdding(false);
              }}
            >
              取消
            </button>
          </div>
        </section>
      )}

      <section className="source-overview">
        <MetricCard label="启用信息源" value={`${enabledCount}`} />
        <MetricCard label="健康" value={`${healthyCount}`} tone="success" />
        <MetricCard label="噪声较高" value={`${noisySources.length}`} tone="warning" />
        <MetricCard label="最近失败" value={`${failedSources.length}`} tone="danger" />
      </section>

      <section className="panel source-filter-panel">
        <label>
          搜索信息源
          <input
            ref={searchRef}
            value={query}
            placeholder="按名称、URL 或标签过滤，快捷键 /"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      </section>

      <section className="panel suggestions-panel">
        <div className="panel-header">
          <div>
            <h2>质量建议</h2>
            <p className="muted">先处理失败和高噪声源，日报会更稳定、更聚焦。</p>
          </div>
        </div>
        {noisySources.length === 0 && failedSources.length === 0 ? (
          <p className="suggestion-good">当前信息源状态良好。</p>
        ) : (
          <div className="suggestion-list">
            {failedSources.slice(0, 3).map((source) => (
              <Suggestion key={`failed-${source.id}`} tone="danger" title={source.name} text="最近读取失败，建议检查地址或代理设置。" />
            ))}
            {noisySources.slice(0, 3).map((source) => (
              <Suggestion key={`noisy-${source.id}`} tone="warning" title={source.name} text="抓取较多但入选较少，可观察后再决定是否禁用。" />
            ))}
          </div>
        )}
      </section>

      {config.sources.length === 0 ? (
        <EmptyState title="没有信息源" description="添加信息源后，这里会显示抓取、入选和失败状态。" />
      ) : visibleSources.length === 0 ? (
        <EmptyState title="没有匹配的信息源" description="换个关键词试试，或清空搜索框查看全部。" />
      ) : (
        <section className="source-list compact">
          {visibleSources.map((source) => (
            <SourceRow
              key={source.id}
              source={source}
              health={sourceHealth.get(source.id) || getSourceHealth(source, sourceStats)}
              onToggle={() => toggleSource(source)}
              demoMode={demoMode}
            />
          ))}
        </section>
      )}
    </div>
  );
}

function SourceRow({ source, health, onToggle, demoMode }: { source: SourceConfig; health: SourceHealth; onToggle: () => void; demoMode: boolean }) {
  const latest = health.latest;
  const status = getStatusLabel(source, health);

  return (
    <article className={health.noisy ? "panel source-card compact noisy" : "panel source-card compact"}>
      <div className="source-main">
        <div className="source-title-line">
          <h2>{source.name}</h2>
          <StatusBadge tone={source.enabled ? "success" : "disabled"}>{source.enabled ? "已启用" : "已禁用"}</StatusBadge>
          <StatusBadge tone={status.tone}>{status.label}</StatusBadge>
          {health.noisy && <StatusBadge tone="noisy">噪声较高</StatusBadge>}
        </div>
        <p className="source-url">{source.url}</p>
        <div className="source-tags">
          <span>{formatSourceType(source.type)}</span>
          {source.tags.slice(0, 3).map((tag) => <span key={tag}>{tag}</span>)}
        </div>
      </div>

      <div className="source-metrics">
        <CompactMeta label="最近抓取" value={formatDateTime(latest?.finishedAt)} />
        <CompactMeta label="抓取" value={formatNumber(latest?.fetchedCount)} />
        <CompactMeta label="入选" value={formatNumber(latest?.selectedCount)} />
        <CompactMeta label="入选率" value={latest ? `${health.selectedRate}%` : "未记录"} />
        <CompactMeta label="近期失败" value={`${health.recentFailures}`} />
      </div>

      <div className="source-actions">
        <button className={source.enabled ? "danger-button small-button" : "secondary small-button"} disabled={demoMode} onClick={onToggle}>
          {source.enabled ? "禁用" : "启用"}
        </button>
        <details>
          <summary>详情</summary>
          <div className="source-detail">
            <p><strong>最近状态：</strong>{latest ? translateRunStatus(latest.status) : "未运行"}</p>
            {latest?.errorMessage && <p className="soft-error">{latest.errorMessage}</p>}
            <p><strong>更新时间：</strong>{formatDateTime(source.updatedAt)}</p>
          </div>
        </details>
      </div>
    </article>
  );
}

function MetricCard({ label, value, tone }: { label: string; value: string; tone?: "success" | "warning" | "danger" }) {
  return (
    <div className={`metric-card ${tone || ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Suggestion({ tone, title, text }: { tone: "warning" | "danger"; title: string; text: string }) {
  return (
    <div className={`suggestion-item ${tone}`}>
      <strong>{title}</strong>
      <span>{text}</span>
    </div>
  );
}

function CompactMeta({ label, value }: { label: string; value: string }) {
  return (
    <div className="compact-meta">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function getSourceHealth(source: SourceConfig, sourceStats: SourceRunStat[]): SourceHealth {
  const stats = sourceStats.filter((stat) => stat.sourceId === source.id);
  const latest = stats[0];
  const recentFailures = stats.slice(0, 5).filter((stat) => stat.status === "failed" || stat.errorMessage).length;
  const selectedRate = latest?.fetchedCount ? Math.round((latest.selectedCount / latest.fetchedCount) * 100) : 0;
  return {
    latest,
    recentFailures,
    selectedRate,
    noisy: Boolean(latest && latest.fetchedCount >= 20 && latest.selectedCount === 0),
  };
}

function getStatusLabel(source: SourceConfig, health: SourceHealth): { label: string; tone: "neutral" | "success" | "failed" | "warning" | "disabled" | "healthy" } {
  if (!source.enabled) return { label: "已禁用", tone: "disabled" };
  if (!health.latest) return { label: "未运行", tone: "neutral" };
  if (health.latest.status === "failed") return { label: "失败", tone: "failed" };
  if (health.latest.status === "partial") return { label: "警告", tone: "warning" };
  return { label: "成功", tone: "healthy" };
}

function translateRunStatus(status: string): string {
  const labels: Record<string, string> = {
    success: "成功",
    failed: "失败",
    partial: "部分成功",
  };
  return labels[status] || status;
}

function formatSourceType(type: string): string {
  const labels: Record<string, string> = {
    rss: "RSS",
    github: "GitHub",
    arxiv: "arXiv",
    blog: "博客",
    custom: "自定义",
  };
  return labels[type] || type;
}

function formatNumber(value?: number): string {
  return value === undefined || Number.isNaN(value) ? "未记录" : String(value);
}

function splitTags(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function isLikelyUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function normalizeUrl(value: string): string {
  return value.trim().replace(/\/+$/, "").toLowerCase();
}

function createSourceId(url: string): string {
  const slug = normalizeUrl(url)
    .replace(/^https?:\/\//, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
  return `src-custom-${slug || Date.now()}`;
}

function matchesSourceQuery(source: SourceConfig, query: string): boolean {
  const value = query.trim().toLowerCase();
  if (!value) return true;
  return [source.name, source.url, source.type, source.priority, ...source.tags].some((item) =>
    item.toLowerCase().includes(value),
  );
}
