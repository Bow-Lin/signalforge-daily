import { useEffect, useState } from "react";
import { ErrorRecoveryCard } from "../components/ErrorRecoveryCard";
import { FeedWarningsCard } from "../components/FeedWarningsCard";
import { RunStatusCard } from "../components/RunStatusCard";
import { TodayOverviewCard } from "../components/TodayOverviewCard";
import { TopPicksList } from "../components/TopPicksList";
import { copyText, generateDigest, openPath, revealPath, saveConfig } from "../services/bridge";
import type { AppSnapshot } from "../types/bridge";
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
  const missingApiKey = !config.aiProvider.apiKey;
  const activeRun = runningRun || latestRun;
  const reportPath = latestReport?.markdownPath || latestRun?.output?.markdownPath;
  const [quickDefaults, setQuickDefaults] = useState(config.digestDefaults);
  const topPicks = latestReport?.topPicks || latestRun?.topPicks || [];

  useEffect(() => {
    setQuickDefaults(config.digestDefaults);
  }, [config.digestDefaults.language, config.digestDefaults.timeRangeHours, config.digestDefaults.topN]);

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

  const copyFavoritePlaceholder = async (title: string, url?: string) => {
    await copyText([title, url].filter(Boolean).join("\n"));
  };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>SignalForge Daily</h1>
          <p className="page-subtitle">每天为你筛选真正重要的 AI / Agent / Coding / EDA 技术信号。</p>
        </div>
        <div className="header-actions">
          <button className="primary-action" onClick={start} disabled={missingApiKey || !!runningRun}>
            {runningRun ? "生成中..." : "生成今日摘要"}
          </button>
          <button className="secondary" onClick={() => onNavigate("settings")}>设置自动生成</button>
        </div>
      </header>

      {missingApiKey && (
        <section className="panel warning-panel">
          <strong>尚未配置 API Key，无法生成摘要。</strong>
          <button className="secondary" onClick={() => onNavigate("settings")}>前往设置</button>
        </section>
      )}

      <TodayOverviewCard run={latestRun} report={latestReport} isRunning={!!runningRun} />

      <TopPicksList
        picks={topPicks}
        onReadReport={() => reportPath && openPath(reportPath)}
        onOpenOriginal={(url) => openPath(url)}
        onFavorite={(pick) => copyFavoritePlaceholder(pick.title, pick.url)}
      />

      <section className="panel report-actions-panel">
        <div className="panel-header">
          <div>
            <h2>完整报告</h2>
            <p className="muted">需要细读、复制或重新生成时再使用这些操作。</p>
          </div>
        </div>
        <div className="actions">
          <button disabled={!reportPath} onClick={() => reportPath && openPath(reportPath)}>打开完整报告</button>
          <button className="secondary" disabled={!topPicks.length} onClick={copyTop3}>复制精选</button>
          <button className="secondary" disabled={missingApiKey || !!runningRun} onClick={start}>重新生成</button>
        </div>
      </section>

      <section className="panel quick-run-panel">
        <div className="panel-header">
          <div>
            <h2>摘要设置</h2>
            <p className="muted">这些默认值会立即保存，并用于下一次生成。</p>
          </div>
        </div>
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
