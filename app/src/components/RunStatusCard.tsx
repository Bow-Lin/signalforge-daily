import { useEffect, useRef } from "react";
import { formatDateTime, formatDuration } from "../services/format";
import type { RunRecord } from "../types/run";

type Props = {
  run?: RunRecord;
  currentStep?: string;
  logs?: string[];
};

export function RunStatusCard({ run, currentStep, logs = [] }: Props) {
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  if (!run) return null;

  return (
    <details className="panel run-details">
      <summary>
        <span>运行详情</span>
        <span className={`status ${run.status}`}>{translateStatus(run.status)}</span>
      </summary>
      <div className="details-content">
        <div className="meta-grid">
          <Meta label="开始时间" value={formatDateTime(run.startedAt)} />
          <Meta label="完成时间" value={formatDateTime(run.finishedAt)} />
          <Meta label="运行耗时" value={formatDuration(run.durationMs)} />
          <Meta label="当前步骤" value={translateStep(currentStep || run.status)} />
          <Meta label="已抓取文章" value={formatNumber(run.stats?.articlesFetched)} />
          <Meta label="报告文件" value={run.output?.markdownPath || run.output?.reportPath || "未记录"} />
        </div>
        {run.warnings?.feedFailures?.length ? (
          <div className="details-list">
            <strong>失败信息源</strong>
            <ul>
              {run.warnings.feedFailures.map((failure) => (
                <li key={`${failure.source}-${failure.reason}`}>
                  <span>{failure.source}</span>
                  <small>{failure.reason}</small>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {run.error && (
          <div className="soft-error">
            <strong>{run.error.message}</strong>
          </div>
        )}
        {logs.length > 0 && (
          <div className="log-box" ref={logRef}>
            {logs.map((line, index) => (
              <div key={`${line}-${index}`}>{line}</div>
            ))}
          </div>
        )}
      </div>
    </details>
  );
}

function translateStatus(status: string): string {
  const labels: Record<string, string> = {
    pending: "等待中",
    running: "生成中",
    success: "已完成",
    failed: "失败",
    cancelled: "已取消",
  };
  return labels[status] || status;
}

function translateStep(step: string): string {
  const labels: Record<string, string> = {
    pending: "等待中",
    running: "生成中",
    success: "已完成",
    failed: "失败",
    cancelled: "已取消",
    "Preparing environment...": "准备运行环境",
    "Fetching feeds...": "读取信息源",
    "Filtering articles...": "筛选文章",
    "Scoring articles...": "评估文章价值",
    "Generating summaries...": "生成摘要",
    "Writing report...": "写入报告",
    Completed: "已完成",
  };
  return labels[step] || step;
}

function formatNumber(value?: number): string {
  if (value === undefined || Number.isNaN(value)) return "未记录";
  return String(value);
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="meta-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
