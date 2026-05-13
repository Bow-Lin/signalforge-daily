import { formatDateTime, isToday } from "../services/format";
import type { ReportRecord } from "../types/report";
import type { RunRecord } from "../types/run";

type Props = {
  run?: RunRecord;
  report?: ReportRecord;
  isRunning: boolean;
};

export function TodayOverviewCard({ run, report, isRunning }: Props) {
  const picks = report?.topPicks || run?.topPicks || [];
  const selectedCount = run?.stats?.articlesSelected ?? report?.selectedCount;
  const sourcesScanned = run?.stats?.sourcesScanned;
  const status = getDigestStatus(run, report, isRunning);
  const generatedAt = run?.finishedAt || report?.generatedAt;

  return (
    <section className="panel today-overview">
      <div className="overview-copy">
        <span className={`status ${status.kind}`}>{status.label}</span>
        <h2>今日摘要</h2>
        <p>
          {buildSummarySentence(sourcesScanned, selectedCount, picks.length)}
        </p>
      </div>
      <div className="overview-stats">
        <OverviewStat label="生成时间" value={formatDateTime(generatedAt)} />
        <OverviewStat label="信息源" value={formatCount(sourcesScanned, "个")} />
        <OverviewStat label="入选文章" value={formatCount(selectedCount, "篇")} />
        <OverviewStat label="重点推荐" value={formatCount(picks.length, "篇")} />
      </div>
    </section>
  );
}

function OverviewStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="overview-stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function getDigestStatus(run: RunRecord | undefined, report: ReportRecord | undefined, isRunning: boolean) {
  if (isRunning) return { label: "生成中", kind: "running" };
  if (run?.status === "failed") return { label: "生成失败", kind: "failed" };
  if (run?.status === "success" || report) {
    return { label: run?.finishedAt && isToday(run.finishedAt) ? "今日已生成" : "已有报告", kind: "success" };
  }
  return { label: "尚未生成", kind: "pending" };
}

function buildSummarySentence(sources?: number, selected?: number, picks?: number): string {
  if (sources || selected || picks) {
    return `已从 ${formatNumber(sources)} 个信息源中筛选出 ${formatNumber(selected)} 条重要更新，其中 ${formatNumber(picks)} 条值得优先阅读。`;
  }
  return "生成后，这里会直接展示今天最值得阅读的技术信号。";
}

function formatCount(value: number | undefined, unit: string): string {
  if (value === undefined || Number.isNaN(value)) return "未记录";
  return `${value} ${unit}`;
}

function formatNumber(value: number | undefined): string {
  return value === undefined || Number.isNaN(value) ? "未记录" : String(value);
}
