import { useEffect, useState } from "react";
import { ErrorRecoveryCard } from "../components/ErrorRecoveryCard";
import { FeedWarningsCard } from "../components/FeedWarningsCard";
import { RunStatusCard } from "../components/RunStatusCard";
import { TodayOverviewCard } from "../components/TodayOverviewCard";
import { TopPicksList } from "../components/TopPicksList";
import { PageHeader } from "../components/ui";
import { getConfigReadiness } from "../services/configReadiness";
import { copyText, generateDigest, getAutomationStatus, openPath, revealPath, saveConfig, saveItemFeedback, setAutomationPaused } from "../services/bridge";
import type { AppSnapshot, AutomationStatus } from "../types/bridge";
import type { AppConfig, DigestLanguage } from "../types/config";
import type { ReportRecord } from "../types/report";
import type { RunRecord } from "../types/run";
import type { RouteId } from "../app/routes";

type Props = {
  config: AppConfig;
  latestRun?: RunRecord;
  latestReport?: ReportRecord;
  runningRun?: RunRecord;
  runLogs: string[];
  currentStep: string;
  onNavigate: (route: RouteId) => void;
  onSnapshot: (snapshot: AppSnapshot | ((snapshot: AppSnapshot) => AppSnapshot)) => void;
};

export function TodayPage({ config, latestRun, latestReport, runningRun, runLogs, currentStep, onNavigate, onSnapshot }: Props) {
  const configReadiness = getConfigReadiness(config);
  const activeRun = runningRun || latestRun;
  const reportPath = latestReport?.markdownPath || latestRun?.output?.markdownPath;
  const [quickDefaults, setQuickDefaults] = useState(config.digestDefaults);
  const [automationStatus, setAutomationStatus] = useState<AutomationStatus | null>(null);
  const topPicks = latestReport?.topPicks || latestRun?.topPicks || [];

  useEffect(() => {
    setQuickDefaults(config.digestDefaults);
  }, [config.digestDefaults.language, config.digestDefaults.timeRangeHours, config.digestDefaults.topN]);

  useEffect(() => {
    getAutomationStatus().then(setAutomationStatus).catch(() => setAutomationStatus(null));
  }, [config.automation.enabled, config.automation.timeOfDay, config.automation.pausedUntil, latestRun?.id]);

  const updateDigestDefaults = async (nextDefaults: AppConfig["digestDefaults"]) => {
    setQuickDefaults(nextDefaults);
    const snapshot = await saveConfig({
      ...config,
      digestDefaults: nextDefaults,
    });
    onSnapshot(snapshot);
  };

  const start = async () => {
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
  };

  const recordFeedback = async (pick: NonNullable<RunRecord["topPicks"]>[number], feedback: "useful" | "not_useful" | "hide_similar") => {
    const itemId = pick.itemId || `${pick.url || pick.title}`;
    const snapshot = await saveItemFeedback({
      itemId,
      reportId: latestReport?.id || latestRun?.id || "latest",
      feedback,
      createdAt: new Date().toISOString(),
    });
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
          <button className="primary-action" onClick={start} disabled={!configReadiness.ready || !!runningRun}>
            {runningRun ? "生成中..." : "生成今日摘要"}
          </button>
          <button className="secondary small-button" onClick={() => onNavigate("settings")}>设置</button>
          </>
        }
      />

      {!configReadiness.ready && (
        <section className="panel warning-panel">
          <strong>基础配置还没有完成，无法生成摘要。</strong>
          <button className="secondary" onClick={() => onNavigate("settings")}>前往设置</button>
        </section>
      )}

      <TodayOverviewCard run={latestRun} report={latestReport} isRunning={!!runningRun} />

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

      <section className="panel report-actions-panel">
        <div className="panel-header">
          <div>
            <h2>完整报告</h2>
            <p className="muted">需要细读、复制或重新生成时再使用这些操作。</p>
          </div>
        </div>
        <div className="actions">
          <button disabled={!reportPath} onClick={() => reportPath && onNavigate("reports")}>预览完整报告</button>
          <button className="secondary" disabled={!reportPath} onClick={() => reportPath && openPath(reportPath)}>打开文件</button>
          <button className="secondary" disabled={!topPicks.length} onClick={copyTop3}>复制精选</button>
          <button className="secondary" disabled={!configReadiness.ready || !!runningRun} onClick={start}>重新生成</button>
        </div>
      </section>

      {latestRun?.status === "failed" && (
        <ErrorRecoveryCard
          run={latestRun}
          onRetry={start}
          onSettings={() => onNavigate("settings")}
          onOpenLogs={() => latestRun.output?.logPath && openPath(latestRun.output.logPath)}
        />
      )}

      <FeedWarningsCard run={latestRun} />

      <details className="panel quick-run-panel">
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
          <button className="secondary" disabled={!latestRun?.output?.logPath} onClick={() => latestRun?.output?.logPath && openPath(latestRun.output.logPath)}>
            查看运行日志
          </button>
        </div>
      </details>
    </div>
  );
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
