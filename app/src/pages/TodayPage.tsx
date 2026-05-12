import { ErrorRecoveryCard } from "../components/ErrorRecoveryCard";
import { LatestDigestCard } from "../components/LatestDigestCard";
import { RunStatusCard } from "../components/RunStatusCard";
import { TopPicksList } from "../components/TopPicksList";
import { copyText, generateDigest, openPath, revealPath } from "../services/bridge";
import type { AppSnapshot } from "../types/bridge";
import type { AppConfig } from "../types/config";
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

export function TodayPage({ config, latestRun, latestReport, runningRun, runLogs, currentStep, onNavigate }: Props) {
  const missingApiKey = !config.aiProvider.apiKey;
  const activeRun = runningRun || latestRun;
  const reportPath = latestReport?.markdownPath || latestRun?.output?.markdownPath;

  const start = async () => {
    await generateDigest();
  };

  const copyTop3 = async () => {
    const picks = latestReport?.topPicks || latestRun?.topPicks || [];
    await copyText(
      picks
        .slice(0, 3)
        .map((pick, index) => `${index + 1}. ${pick.title}${pick.source ? ` - ${pick.source}` : ""}${pick.reason ? `\n   ${pick.reason}` : ""}`)
        .join("\n"),
    );
  };

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <span className="eyebrow">Today</span>
          <h1>AI technical digest</h1>
        </div>
        <button className="primary-action" onClick={start} disabled={missingApiKey || !!runningRun}>
          {runningRun ? "Generating..." : "Generate Today's Digest"}
        </button>
      </header>

      {missingApiKey && (
        <section className="panel warning-panel">
          <strong>API key is not configured.</strong>
          <button className="secondary" onClick={() => onNavigate("settings")}>Go to Settings</button>
        </section>
      )}

      {latestRun?.status === "failed" && (
        <ErrorRecoveryCard
          run={latestRun}
          onRetry={start}
          onSettings={() => onNavigate("settings")}
          onOpenLogs={() => latestRun.output?.logPath && openPath(latestRun.output.logPath)}
        />
      )}

      <LatestDigestCard
        run={latestRun}
        report={latestReport}
        onOpen={() => reportPath && openPath(reportPath)}
        onReveal={() => reportPath && revealPath(reportPath)}
      />

      <TopPicksList picks={latestReport?.topPicks || latestRun?.topPicks} />

      <RunStatusCard run={activeRun} currentStep={currentStep} logs={runLogs} />

      <section className="panel">
        <div className="panel-header">
          <h2>Actions</h2>
        </div>
        <div className="actions">
          <button className="secondary" disabled={!reportPath} onClick={() => reportPath && openPath(reportPath)}>Open Latest Report</button>
          <button className="secondary" disabled={!reportPath} onClick={() => reportPath && revealPath(reportPath)}>Reveal in Folder</button>
          <button className="secondary" disabled={!latestReport?.topPicks?.length && !latestRun?.topPicks?.length} onClick={copyTop3}>Copy Top 3</button>
          <button className="secondary" disabled={missingApiKey || !!runningRun} onClick={start}>Retry Last Run</button>
        </div>
      </section>
    </div>
  );
}
