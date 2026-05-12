import { useMemo, useState } from "react";
import { MarkdownPreview } from "../components/MarkdownPreview";
import { deleteRun, revealPath } from "../services/bridge";
import { formatDateTime } from "../services/format";
import type { AppSnapshot } from "../types/bridge";
import type { ReportRecord } from "../types/report";

type Props = {
  reports: ReportRecord[];
  onSnapshot: (snapshot: AppSnapshot) => void;
};

export function ReportsPage({ reports, onSnapshot }: Props) {
  const [selectedId, setSelectedId] = useState(reports[0]?.id || "");
  const selected = useMemo(() => reports.find((report) => report.id === selectedId) || reports[0], [reports, selectedId]);

  const removeFromList = async (report: ReportRecord) => {
    if (!report.runId) return;
    const next = await deleteRun(report.runId);
    onSnapshot(next);
  };

  return (
    <div className="page reports-page">
      <header className="page-header">
        <div>
          <span className="eyebrow">Reports</span>
          <h1>Digest history</h1>
        </div>
      </header>
      <div className="reports-layout">
        <section className="report-list">
          {reports.length === 0 ? (
            <div className="panel empty">
              <h2>No reports yet</h2>
              <p>Generated digest reports will appear here.</p>
            </div>
          ) : (
            reports.map((report) => (
              <button
                key={report.id}
                className={selected?.id === report.id ? "report-item selected" : "report-item"}
                onClick={() => setSelectedId(report.id)}
              >
                <strong>{report.title}</strong>
                <span>Generated: {formatDateTime(report.generatedAt)}</span>
                <span>Selected: {report.selectedCount ?? "Unknown"} · Language: {report.language === "zh" ? "中文" : "English"} · Status: Success</span>
                <div className="item-actions">
                  <span onClick={(event) => { event.stopPropagation(); revealPath(report.markdownPath); }}>Reveal in Folder</span>
                  {report.runId && <span onClick={(event) => { event.stopPropagation(); removeFromList(report); }}>Delete from list</span>}
                </div>
              </button>
            ))
          )}
        </section>
        <MarkdownPreview report={selected} />
      </div>
    </div>
  );
}
