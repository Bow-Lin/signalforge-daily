import { useEffect, useRef, useState } from "react";
import { ErrorRecoveryCard } from "../components/ErrorRecoveryCard";
import { FeedWarningsCard } from "../components/FeedWarningsCard";
import { RunStatusCard } from "../components/RunStatusCard";
import { TodayOverviewCard } from "../components/TodayOverviewCard";
import { TopPicksList } from "../components/TopPicksList";
import { PageHeader } from "../components/ui";
import { getConfigReadiness } from "../services/configReadiness";
import { copyText, deleteItemFeedback, generateDigest, getAutomationStatus, openPath, revealPath, saveConfig, saveItemFeedback, setAutomationPaused } from "../services/bridge";
import type { AppSnapshot, AutomationStatus } from "../types/bridge";
import type { AppConfig, DigestLanguage } from "../types/config";
import type { ReportRecord } from "../types/report";
import type { ItemFeedback, RunRecord } from "../types/run";
import type { RouteId } from "../app/routes";
import type { ToastItem } from "../components/ui";
import type { UiState } from "../services/uiState";

type Props = {
  config: AppConfig;
  latestRun?: RunRecord;
  latestReport?: ReportRecord;
  runningRun?: RunRecord;
  runLogs: string[];
  currentStep: string;
  onNavigate: (route: RouteId) => void;
  onSnapshot: (snapshot: AppSnapshot | ((snapshot: AppSnapshot) => AppSnapshot)) => void;
  demoMode?: boolean;
  uiState: UiState;
  onUiStateChange: (patch: Partial<UiState>) => void;
  focusRequest?: { target: "latest" | "error"; nonce: number } | null;
  onToast: (toast: Omit<ToastItem, "id">) => string;
  itemFeedback: ItemFeedback[];
};

export function TodayPage({
  config,
  latestRun,
  latestReport,
  runningRun,
  runLogs,
  currentStep,
  onNavigate,
  onSnapshot,
  demoMode = false,
  uiState,
  onUiStateChange,
  focusRequest,
  onToast,
  itemFeedback,
}: Props) {
  const configReadiness = getConfigReadiness(config);
  const activeRun = runningRun || latestRun;
  const reportPath = latestReport?.markdownPath || latestRun?.output?.markdownPath;
  const [quickDefaults, setQuickDefaults] = useState(config.digestDefaults);
  const [automationStatus, setAutomationStatus] = useState<AutomationStatus | null>(null);
  const latestResultRef = useRef<HTMLDivElement>(null);
  const errorRecoveryRef = useRef<HTMLDivElement>(null);
  const topPicks = latestReport?.topPicks || latestRun?.topPicks || [];

  useEffect(() => {
    setQuickDefaults(config.digestDefaults);
  }, [config.digestDefaults.language, config.digestDefaults.timeRangeHours, config.digestDefaults.topN]);

  useEffect(() => {
    getAutomationStatus().then(setAutomationStatus).catch(() => setAutomationStatus(null));
  }, [config.automation.enabled, config.automation.timeOfDay, config.automation.pausedUntil, latestRun?.id]);

  useEffect(() => {
    if (!focusRequest) return;
    const target = focusRequest.target === "error" ? errorRecoveryRef.current : latestResultRef.current;
    target?.scrollIntoView({ behavior: "smooth", block: "start" });
    target?.focus({ preventScroll: true });
  }, [focusRequest?.nonce, focusRequest?.target]);

  const updateDigestDefaults = async (nextDefaults: AppConfig["digestDefaults"]) => {
    setQuickDefaults(nextDefaults);
    const snapshot = await saveConfig({
      ...config,
      digestDefaults: nextDefaults,
    });
    onSnapshot(snapshot);
  };

  const start = async () => {
    if (demoMode) return;
    if (
      quickDefaults.language !== config.digestDefaults.language ||
      quickDefaults.timeRangeHours !== config.digestDefaults.timeRangeHours ||
      quickDefaults.topN !== config.digestDefaults.topN
    ) {
      const snapshot = await saveConfig({
        ...config,
        digestDefaults: quickDefaults,
      });
      onSnapshot(snapshot);
    }
    await generateDigest();
  };

  const copyTop3 = async () => {
    await copyText(
      topPicks
        .slice(0, 3)
        .map((pick, index) => `${index + 1}. ${pick.title}${pick.source ? ` - ${pick.source}` : ""}${pick.reason ? `\n   ${pick.reason}` : ""}`)
        .join("\n"),
    );
    onToast({ title: "已复制精选", description: "前三条精选已复制到剪贴板。" });
  };

  const recordFeedback = async (pick: NonNullable<RunRecord["topPicks"]>[number], feedback: "useful" | "not_useful" | "hide_similar") => {
    const itemId = pick.itemId || `${pick.url || pick.title}`;
    const reportId = latestReport?.id || latestRun?.id || "latest";
    const previous = itemFeedback.find((item) => item.itemId === itemId && item.reportId === reportId);
    if (demoMode) {
      onSnapshot((current) => ({
        ...current,
        feedback: [
          { itemId, reportId, feedback, createdAt: new Date().toISOString() },
          ...current.feedback.filter((item) => !(item.itemId === itemId && item.reportId === reportId)),
        ],
      }));
      onToast({ title: feedbackLabel(feedback), actionLabel: "撤销", onAction: () => undoFeedback(itemId, reportId, previous, true) });
      return;
    }
    const snapshot = await saveItemFeedback({
      itemId,
      reportId,
      feedback,
      createdAt: new Date().toISOString(),
    });
    onSnapshot(snapshot);
    onToast({ title: feedbackLabel(feedback), actionLabel: "撤销", onAction: () => undoFeedback(itemId, reportId, previous, false) });
  };

  const undoFeedback = async (itemId: string, reportId: string, previous: ItemFeedback | undefined, demoUndo: boolean) => {
    if (demoUndo) {
      onSnapshot((current) => ({
        ...current,
        feedback: previous
          ? [previous, ...current.feedback.filter((item) => !(item.itemId === itemId && item.reportId === reportId))]
          : current.feedback.filter((item) => !(item.itemId === itemId && item.reportId === reportId)),
      }));
      return;
    }
    const snapshot = previous ? await saveItemFeedback(previous) : await deleteItemFeedback(itemId, reportId);
    onSnapshot(snapshot);
  };

  const toggleAutomationPause = async () => {
    const snapshot = await setAutomationPaused(!automationStatus?.paused);
    onSnapshot(snapshot);
    const status = await getAutomationStatus();
    setAutomationStatus(status);
  };

  return (
    <div className="page">
      <PageHeader
        title="SignalForge Daily"
        description="每天为你筛选真正重要的 AI / Agent / Coding / EDA 技术信号。"
        actions={
          <>
          <button className="secondary small-button" disabled={!reportPath} onClick={() => reportPath && onNavigate("reports")} title="快捷键 Ctrl/Cmd+O">
            查看最新报告
          </button>
          <button className="secondary small-button" disabled={!topPicks.length} onClick={copyTop3}>
            复制精选
          </button>
          <button className="primary-action" onClick={start} disabled={demoMode || !configReadiness.ready || !!runningRun}>
            {demoMode ? "Demo 样例" : runningRun ? "生成中..." : latestRun ? "重新生成" : "生成今日摘要"}
          </button>
          <button className="secondary small-button" onClick={() => onNavigate("settings")} title="快捷键 Ctrl/Cmd+,">设置</button>
          </>
        }
      />

      {!demoMode && !configReadiness.ready && (
        <section className="panel warning-panel">
          <strong>基础配置还没有完成，无法生成摘要。</strong>
          <button className="secondary" onClick={() => onNavigate("settings")}>前往设置</button>
        </section>
      )}

      <div ref={latestResultRef} tabIndex={-1}>
        <TodayOverviewCard run={latestRun} report={latestReport} isRunning={!!runningRun} />
      </div>

      <section className="panel automation-status-card">
        <div>
          <strong>{automationHeadline(config, automationStatus)}</strong>
          <p className="muted">{automationDetail(config, automationStatus)}</p>
        </div>
        <div className="actions">
          <button className="ghost-action small-button" onClick={() => onNavigate("settings")}>修改自动化设置</button>
          {config.automation.enabled && (
            <button className="ghost-action small-button" onClick={toggleAutomationPause}>
              {automationStatus?.paused ? "恢复" : "暂停"}
            </button>
          )}
        </div>
      </section>

      <TopPicksList
        picks={topPicks}
        onReadReport={() => reportPath && onNavigate("reports")}
        onOpenOriginal={(url) => openPath(url)}
        onFeedback={recordFeedback}
      />

      {latestRun?.status === "failed" && (
        <div ref={errorRecoveryRef} tabIndex={-1}>
          <ErrorRecoveryCard
            run={latestRun}
            onRetry={start}
            onSettings={() => onNavigate("settings")}
            onOpenLogs={() => latestRun.output?.logPath && openPath(latestRun.output.logPath)}
          />
        </div>
      )}

      <FeedWarningsCard run={latestRun} />

      <details
        className="panel quick-run-panel"
        open={uiState.todayQuickSettingsOpen}
        onToggle={(event) => onUiStateChange({ todayQuickSettingsOpen: event.currentTarget.open })}
      >
        <summary>
          <span>本次生成设置</span>
          <span className="muted">{quickDefaults.language === "zh" ? "中文" : "英文"} · {quickDefaults.timeRangeHours}h</span>
        </summary>
        <div className="details-content">
          <p className="muted">Today 只显示当前值；需要调整完整默认项可进入设置。</p>
          <div className="quick-run-grid">
          <label>
            语言
            <select
              value={quickDefaults.language}
              disabled={!!runningRun}
              onChange={(event) =>
                updateDigestDefaults({
                  ...quickDefaults,
                  language: event.target.value as DigestLanguage,
                })
              }
            >
              <option value="zh">中文</option>
              <option value="en">英文</option>
            </select>
          </label>
          <label>
            时间范围
            <select
              value={quickDefaults.timeRangeHours}
              disabled={!!runningRun}
              onChange={(event) =>
                updateDigestDefaults({
                  ...quickDefaults,
                  timeRangeHours: Number(event.target.value),
                })
              }
            >
              <option value={24}>24h</option>
              <option value={48}>48h</option>
              <option value={72}>72h</option>
              <option value={168}>7d</option>
            </select>
          </label>
          </div>
          <button className="ghost-action" onClick={() => onNavigate("settings")}>修改默认设置</button>
        </div>
      </details>

      <RunStatusCard run={activeRun} currentStep={currentStep} logs={runLogs} />

      <details className="more-actions">
        <summary>更多操作</summary>
        <div className="actions">
          <button className="secondary" disabled={!reportPath} onClick={() => reportPath && revealPath(reportPath)}>在文件夹中显示</button>
          <button className="secondary" disabled={!reportPath} onClick={() => reportPath && openPath(reportPath)}>用默认应用打开报告</button>
          <button className="secondary" disabled={!latestRun?.output?.logPath} onClick={() => latestRun?.output?.logPath && openPath(latestRun.output.logPath)}>
            查看运行日志
          </button>
        </div>
      </details>
    </div>
  );
}

function feedbackLabel(feedback: "useful" | "not_useful" | "hide_similar"): string {
  const labels = {
    useful: "已标记为有用",
    not_useful: "已标记为不感兴趣",
    hide_similar: "已记录隐藏类似内容",
  };
  return labels[feedback];
}

function automationHeadline(config: AppConfig, status: AutomationStatus | null): string {
  if (!config.automation.enabled) return "自动生成未开启";
  if (status?.paused) return "自动生成已暂停";
  return "自动生成已开启";
}

function automationDetail(config: AppConfig, status: AutomationStatus | null): string {
  if (!config.automation.enabled) return "需要每天自动准备日报时，可以在设置中开启。";
  if (status?.paused) return "恢复后会按默认时间继续准备日报。";
  if (status?.nextRunAt) {
    return `下一次运行：${new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(status.nextRunAt))}`;
  }
  return `下一次运行时间会按 ${config.automation.timeOfDay} 计算。`;
}
