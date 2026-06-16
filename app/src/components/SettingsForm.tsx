import { useEffect, useState } from "react";
import { chooseFolder, generateDigest, getAutomationStatus, saveConfig, setAutomationPaused, testConnection } from "../services/bridge";
import { getConfigReadiness } from "../services/configReadiness";
import { ensureNotificationPermission, getNotificationPermission, notify, type NotificationPermissionState } from "../services/notificationService";
import type { ToastItem } from "./ui";
import type { AppSnapshot, AutomationStatus } from "../types/bridge";
import { defaultConfig, type AppConfig } from "../types/config";
import type { UiState } from "../services/uiState";

type Props = {
  config: AppConfig | null;
  onSaved: (snapshot: AppSnapshot) => void;
  compact?: boolean;
  uiState?: UiState;
  onUiStateChange?: (patch: Partial<UiState>) => void;
  onToast?: (toast: Omit<ToastItem, "id">) => string;
};

export function SettingsForm({ config, onSaved, compact = false, uiState, onUiStateChange, onToast }: Props) {
  const [draft, setDraft] = useState<AppConfig>(config || defaultConfig());
  const [showKey, setShowKey] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(uiState?.settingsAdvancedOpen ?? false);
  const [networkOpen, setNetworkOpen] = useState(uiState?.settingsNetworkOpen ?? false);
  const [message, setMessage] = useState("");
  const [testMessage, setTestMessage] = useState("");
  const [testOk, setTestOk] = useState(false);
  const [testing, setTesting] = useState(false);
  const [automationStatus, setAutomationStatus] = useState<AutomationStatus | null>(null);
  const [notificationPermission, setNotificationPermission] = useState<NotificationPermissionState>("prompt");
  const [interestedDraft, setInterestedDraft] = useState(draft.relevanceProfile.interestedTopics.join(", "));
  const [mutedDraft, setMutedDraft] = useState(draft.relevanceProfile.mutedTopics.join(", "));

  useEffect(() => {
    getAutomationStatus().then(setAutomationStatus).catch(() => setAutomationStatus(null));
    getNotificationPermission().then(setNotificationPermission);
  }, []);

  const update = <T extends keyof AppConfig>(section: T, value: Partial<AppConfig[T]>) => {
    if (section === "aiProvider" || section === "network") setTestOk(false);
    setDraft((current) => ({
      ...current,
      [section]: { ...(current[section] as object), ...value },
    }));
  };

  const updateAutomation = (value: Partial<AppConfig["automation"]>) => {
    setDraft((current) => ({
      ...current,
      automation: { ...current.automation, ...value },
    }));
  };

  const pickWorkspace = async () => {
    const folder = await chooseFolder();
    if (!folder) return;
    setTestOk(false);
    setDraft((current) => ({
      ...current,
      workspacePath: folder,
      outputPath: current.outputPath || `${folder}/reports`,
    }));
  };

  const save = async () => {
    try {
      const previousConfig = config;
      const next = await saveConfig(draft);
      setMessage(compact ? "配置已保存，正在进入 Today。" : "配置已保存。");
      onSaved(next);
      getAutomationStatus().then(setAutomationStatus).catch(() => setAutomationStatus(null));
      onToast?.({
        title: "设置已保存",
        description: compact ? "可以开始生成摘要。" : "本地配置已更新。",
        actionLabel: previousConfig ? "撤销" : undefined,
        onAction: previousConfig
          ? async () => {
              const restored = await saveConfig(previousConfig);
              setDraft(restored.config || previousConfig);
              onSaved(restored);
            }
          : undefined,
      });
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    }
  };

  const testNotification = async () => {
    const permission = await ensureNotificationPermission();
    setNotificationPermission(permission);
    if (permission === "granted") {
      await notify("SignalForge Daily 通知已开启", "之后自动生成成功或失败时，你会收到提醒。");
    }
  };

  const pauseAutomation = async () => {
    const next = await setAutomationPaused(!automationStatus?.paused);
    onSaved(next);
    setDraft(next.config || draft);
    getAutomationStatus().then(setAutomationStatus).catch(() => setAutomationStatus(null));
  };

  const test = async () => {
    setTesting(true);
    setTestMessage("");
    try {
      const result = await testConnection(draft);
      setTestMessage(result.message);
      setTestOk(result.ok);
    } catch (err) {
      setTestOk(false);
      setTestMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setTesting(false);
    }
  };

  const readiness = getConfigReadiness(draft);
  const canTest = draft.aiProvider.apiKey.trim().length > 0 && draft.aiProvider.model.trim().length > 0;
  const canSave = compact ? readiness.ready && testOk : draft.workspacePath.trim().length > 0;

  return (
    <div className="settings-form">
      <section className="panel">
        <h2>工作区</h2>
        <label>
          工作区文件夹
          <div className="inline-field">
            <input value={draft.workspacePath} onChange={(event) => { setTestOk(false); setDraft({ ...draft, workspacePath: event.target.value }); }} />
            <button className="secondary" onClick={pickWorkspace}>选择</button>
          </div>
        </label>
        <label>
          报告输出文件夹
          <input value={draft.outputPath} onChange={(event) => { setTestOk(false); setDraft({ ...draft, outputPath: event.target.value }); }} />
        </label>
      </section>

      <section className="panel">
        <h2>AI Provider</h2>
        <label>
          Provider 类型
          <select value={draft.aiProvider.provider} onChange={(event) => update("aiProvider", { provider: event.target.value as AppConfig["aiProvider"]["provider"] })}>
            <option value="iflow">iFlow</option>
            <option value="openai_compatible">OpenAI compatible</option>
            <option value="custom">Custom</option>
          </select>
        </label>
        <label>
          API Key
          <div className="inline-field">
            <input
              type={showKey ? "text" : "password"}
              value={draft.aiProvider.apiKey}
              onChange={(event) => update("aiProvider", { apiKey: event.target.value })}
            />
            <button className="secondary" onClick={() => setShowKey((value) => !value)}>{showKey ? "隐藏" : "显示"}</button>
          </div>
        </label>
        <label>
          Base URL
          <input value={draft.aiProvider.baseUrl || ""} onChange={(event) => update("aiProvider", { baseUrl: event.target.value })} />
        </label>
        <label>
          模型
          <input value={draft.aiProvider.model} onChange={(event) => update("aiProvider", { model: event.target.value })} />
        </label>
        <div className="actions">
          <button className="secondary" onClick={test} disabled={testing || !canTest}>{testing ? "测试中..." : "测试连接"}</button>
          {!testMessage && <span className="status pending">未测试</span>}
          {testMessage && <span className={testMessage.includes("passed") || testMessage.includes("成功") ? "status success" : testMessage.includes("failed") || testMessage.includes("not configured") || testMessage.includes("is not") ? "status failed" : "muted"}>{testOk ? "连接成功" : `连接失败：${testMessage}`}</span>}
        </div>
      </section>

      <section className="panel">
        <h2>相关性偏好</h2>
        <label>
          关注主题
          <input
            value={interestedDraft}
            onChange={(event) => {
              setInterestedDraft(event.target.value);
              update("relevanceProfile", { interestedTopics: splitTopics(event.target.value) });
            }}
            placeholder="agent, coding, EDA"
          />
        </label>
        <label>
          屏蔽主题
          <input
            value={mutedDraft}
            onChange={(event) => {
              setMutedDraft(event.target.value);
              update("relevanceProfile", { mutedTopics: splitTopics(event.target.value) });
            }}
            placeholder="funding, crypto"
          />
        </label>
        <div className="checkbox-grid">
          {contentTypes.map((type) => (
            <label className="checkbox-line" key={type}>
              <input
                type="checkbox"
                checked={draft.relevanceProfile.preferredContentTypes.includes(type)}
                onChange={(event) => {
                  const current = draft.relevanceProfile.preferredContentTypes;
                  update("relevanceProfile", {
                    preferredContentTypes: event.target.checked
                      ? [...current, type]
                      : current.filter((item) => item !== type),
                  });
                }}
              />
              {contentTypeLabel(type)}
            </label>
          ))}
        </div>
        <label>
          语言偏好
          <select value={draft.relevanceProfile.language} onChange={(event) => update("relevanceProfile", { language: event.target.value as AppConfig["relevanceProfile"]["language"] })}>
            <option value="mixed">混合</option>
            <option value="zh">中文</option>
            <option value="en">英文</option>
          </select>
        </label>
      </section>

      <section className="panel">
        <h2>摘要默认值</h2>
        <div className="field-grid">
          <label>
            默认语言
            <select value={draft.digestDefaults.language} onChange={(event) => update("digestDefaults", { language: event.target.value as AppConfig["digestDefaults"]["language"] })}>
              <option value="zh">中文</option>
              <option value="en">英文</option>
            </select>
          </label>
          <label>
            默认时间范围
            <select value={draft.digestDefaults.timeRangeHours} onChange={(event) => update("digestDefaults", { timeRangeHours: Number(event.target.value) })}>
              <option value={24}>24h</option>
              <option value={48}>48h</option>
              <option value={72}>72h</option>
              <option value={168}>7d</option>
            </select>
          </label>
          <label>
            默认 Top N
            <input type="number" min={1} max={50} value={draft.digestDefaults.topN} onChange={(event) => update("digestDefaults", { topN: Number(event.target.value) })} />
          </label>
        </div>
      </section>

      {!compact && (
        <section className="panel automation-settings">
          <div className="panel-header">
            <div>
              <h2>自动化</h2>
              <p className="muted">让 SignalForge Daily 每天在指定时间准备好日报。</p>
            </div>
            <span className={draft.automation.enabled ? "status success" : "status pending"}>
              {draft.automation.enabled ? "已开启" : "未开启"}
            </span>
          </div>
          <div className="field-grid">
            <label className="checkbox-line toggle-line">
              <input
                type="checkbox"
                checked={draft.automation.enabled}
                onChange={(event) => updateAutomation({ enabled: event.target.checked, pausedUntil: event.target.checked ? undefined : draft.automation.pausedUntil })}
              />
              自动生成日报
            </label>
            <label>
              运行频率
              <select value={draft.automation.frequency} onChange={(event) => updateAutomation({ frequency: event.target.value as AppConfig["automation"]["frequency"] })}>
                <option value="daily">每天</option>
                <option value="weekdays">工作日</option>
              </select>
            </label>
            <label>
              运行时间
              <input type="time" value={draft.automation.timeOfDay} onChange={(event) => updateAutomation({ timeOfDay: event.target.value })} />
            </label>
          </div>
          <div className="checkbox-grid">
            <label className="checkbox-line">
              <input type="checkbox" checked={draft.automation.notifyOnSuccess} onChange={(event) => updateAutomation({ notifyOnSuccess: event.target.checked })} />
              生成成功后通知
            </label>
            <label className="checkbox-line">
              <input type="checkbox" checked={draft.automation.notifyOnFailure} onChange={(event) => updateAutomation({ notifyOnFailure: event.target.checked })} />
              生成失败后通知
            </label>
            <label className="checkbox-line">
              <input type="checkbox" checked={draft.automation.runOnAppStartIfMissed} onChange={(event) => updateAutomation({ runOnAppStartIfMissed: event.target.checked })} />
              启动时补跑错过的任务
            </label>
            <label className="checkbox-line">
              <input type="checkbox" checked={draft.automation.skipIfAlreadyGeneratedToday} onChange={(event) => updateAutomation({ skipIfAlreadyGeneratedToday: event.target.checked })} />
              今天已生成则跳过
            </label>
          </div>
          <div className="meta-grid automation-meta">
            <Meta label="下一次自动运行" value={formatDateTime(automationStatus?.nextRunAt)} />
            <Meta label="上一次自动运行" value={formatAutomationRun(automationStatus)} />
            <Meta label="通知权限" value={notificationPermissionLabel(notificationPermission)} />
          </div>
          {automationStatus?.lastSkipReason && <p className="muted">{automationStatus.lastSkipReason}</p>}
          <div className="actions">
            <button className="secondary" onClick={testNotification}>测试通知</button>
            <button className="secondary" onClick={() => generateDigest()} disabled={!readiness.ready}>立即运行一次</button>
            <button className="ghost-action" onClick={pauseAutomation}>
              {automationStatus?.paused ? "恢复自动生成" : "暂停自动生成"}
            </button>
          </div>
        </section>
      )}

      <details
        className="panel settings-details"
        open={networkOpen}
        onToggle={(event) => {
          setNetworkOpen(event.currentTarget.open);
          onUiStateChange?.({ settingsNetworkOpen: event.currentTarget.open });
        }}
      >
        <summary>网络</summary>
        <label>
          代理模式
          <select value={draft.network.proxyMode} onChange={(event) => update("network", { proxyMode: event.target.value as AppConfig["network"]["proxyMode"] })}>
            <option value="system">使用系统代理</option>
            <option value="none">不使用代理</option>
            <option value="custom">自定义代理</option>
          </select>
        </label>
        {draft.network.proxyMode === "custom" && (
          <div className="field-grid">
            <label>
              HTTP 代理
              <input value={draft.network.httpProxy || ""} onChange={(event) => update("network", { httpProxy: event.target.value })} />
            </label>
            <label>
              HTTPS 代理
              <input value={draft.network.httpsProxy || ""} onChange={(event) => update("network", { httpsProxy: event.target.value })} />
            </label>
          </div>
        )}
      </details>

      {!compact && (
        <details
          className="panel settings-details"
          open={advancedOpen}
          onToggle={(event) => {
            setAdvancedOpen(event.currentTarget.open);
            onUiStateChange?.({ settingsAdvancedOpen: event.currentTarget.open });
          }}
        >
          <summary>高级</summary>
          {advancedOpen && (
            <div className="field-grid">
              <label>
                信息源并发
                <input type="number" min={1} value={draft.advanced.feedConcurrency || 10} onChange={(event) => update("advanced", { feedConcurrency: Number(event.target.value) })} />
              </label>
              <label>
                AI 重试次数
                <input type="number" min={0} value={draft.advanced.aiRetries || 1} onChange={(event) => update("advanced", { aiRetries: Number(event.target.value) })} />
              </label>
              <label>
                AI 最大处理文章数
                <input type="number" min={1} value={draft.advanced.maxAiArticles || 120} onChange={(event) => update("advanced", { maxAiArticles: Number(event.target.value) })} />
              </label>
            </div>
          )}
        </details>
      )}

      <div className="sticky-actions">
        {message && <span>{message}</span>}
        {compact && !readiness.ready && <span className="status pending">请补全工作区、输出路径、API Key 和模型</span>}
        {compact && readiness.ready && !testOk && <span className="status pending">请先完成连接测试</span>}
        <button onClick={save} disabled={!canSave}>{compact ? "进入 Today" : "保存设置"}</button>
      </div>
    </div>
  );
}

const contentTypes: AppConfig["relevanceProfile"]["preferredContentTypes"] = [
  "engineering_blog",
  "research_paper",
  "open_source_release",
  "product_update",
  "funding_news",
  "opinion",
];

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="meta-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatDateTime(value?: string): string {
  if (!value) return "未设置";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatAutomationRun(status: AutomationStatus | null): string {
  const run = status?.lastAutomationRun;
  if (!run) return "未运行";
  const label = run.status === "success" ? "成功" : run.status === "failed" ? "失败" : "运行中";
  return `${label} · ${formatDateTime(run.finishedAt || run.startedAt)}`;
}

function notificationPermissionLabel(permission: NotificationPermissionState): string {
  const labels: Record<NotificationPermissionState, string> = {
    granted: "已授权",
    denied: "已拒绝",
    prompt: "未授权",
    unsupported: "不可用",
  };
  return labels[permission];
}

function splitTopics(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function contentTypeLabel(type: AppConfig["relevanceProfile"]["preferredContentTypes"][number]): string {
  const labels: Record<string, string> = {
    engineering_blog: "工程博客",
    research_paper: "研究论文",
    open_source_release: "开源发布",
    product_update: "产品更新",
    funding_news: "融资新闻",
    opinion: "观点评论",
  };
  return labels[type] || type;
}
