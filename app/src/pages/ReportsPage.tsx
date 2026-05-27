import { useMemo, useState } from "react";
import { MarkdownPreview } from "../components/MarkdownPreview";
import { EmptyState, PageHeader, StatusBadge } from "../components/ui";
import { deleteReport, removeReportFromHistory, revealPath } from "../services/bridge";
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
    const next = await removeReportFromHistory(report);
    onSnapshot(next);
    if (selected?.id === report.id) {
      setSelectedId(next.reports[0]?.id || "");
    }
  };

  const deleteSelectedReport = async (report: ReportRecord) => {
    const confirmed = window.confirm(`确定要删除这份报告吗？\n\n${report.title}\n\n该操作会删除本地 Markdown 文件，无法在应用内撤销。`);
    if (!confirmed) return;
    const next = await deleteReport(report);
    onSnapshot(next);
    if (selected?.id === report.id) {
      setSelectedId(next.reports[0]?.id || "");
    }
  };

  return (
    <div className="page reports-page">
      <PageHeader
        eyebrow="REPORTS"
        title="报告历史"
        description="阅读、复制和回溯每一次本地生成的 Daily Digest。"
      />
      <div className="reports-layout">
        <section className="report-list">
          {reports.length === 0 ? (
            <EmptyState title="没有报告" description="生成摘要后，历史报告会出现在这里。" />
          ) : (
            reports.map((report) => (
              <button
                key={report.id}
                className={selected?.id === report.id ? "report-item selected" : "report-item"}
                onClick={() => setSelectedId(report.id)}
              >
                <strong>{report.title}</strong>
                <span>{formatDateTime(report.generatedAt)}</span>
                <div className="report-item-meta">
                  <StatusBadge tone="success">成功</StatusBadge>
                  <span>{report.selectedCount ?? "未记录"} 条入选</span>
                  <span>{report.language === "zh" ? "中文" : "英文"}</span>
                </div>
                <div className="item-actions">
                  <span onClick={(event) => { event.stopPropagation(); revealPath(report.markdownPath); }}>在文件夹中显示</span>
                  <span onClick={(event) => { event.stopPropagation(); removeFromList(report); }}>从列表移除</span>
                  <span className="danger-link" onClick={(event) => { event.stopPropagation(); deleteSelectedReport(report); }}>删除报告</span>
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
