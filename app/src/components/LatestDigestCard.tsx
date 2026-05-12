import { formatDateTime, isToday } from "../services/format";
import type { ReportRecord } from "../types/report";
import type { RunRecord } from "../types/run";

type Props = {
  run?: RunRecord;
  report?: ReportRecord;
  onOpen?: () => void;
  onReveal?: () => void;
};

export function LatestDigestCard({ run, report, onOpen, onReveal }: Props) {
  if (!run && !report) {
    return (
      <section className="panel empty">
        <h2>No digest generated yet.</h2>
        <p>Configure your workspace and generate your first digest.</p>
      </section>
    );
  }

  const status = run?.status === "success" && isToday(run.finishedAt) ? "Success today" : run?.status || "Available";

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Latest Digest</h2>
        <span className={`status ${run?.status || "success"}`}>{status}</span>
      </div>
      <div className="meta-grid">
        <Meta label="Generated" value={formatDateTime(run?.finishedAt || report?.generatedAt)} />
        <Meta label="Sources scanned" value={String(run?.stats?.sourcesScanned ?? "Unknown")} />
        <Meta label="Articles fetched" value={String(run?.stats?.articlesFetched ?? "Unknown")} />
        <Meta label="Selected" value={String(run?.stats?.articlesSelected ?? report?.selectedCount ?? "Unknown")} />
        <Meta label="Language" value={run?.paramsSnapshot.language === "en" ? "English" : "中文"} />
        <Meta label="Report" value={report?.markdownPath || run?.output?.markdownPath || "Not available"} wide />
      </div>
      <div className="actions">
        <button onClick={onOpen} disabled={!report && !run?.output?.markdownPath}>Open Latest Report</button>
        <button className="secondary" onClick={onReveal} disabled={!report && !run?.output?.markdownPath}>Reveal in Folder</button>
      </div>
    </section>
  );
}

function Meta({ label, value, wide }: { label: string; value: string; wide?: boolean }) {
  return (
    <div className={wide ? "meta-item wide" : "meta-item"}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
