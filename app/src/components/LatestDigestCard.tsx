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
        <h2>还没有生成摘要</h2>
        <p>完成工作区配置后，就可以生成第一份 Daily Digest。</p>
      </section>
    );
  }

  const status = run?.status === "success" && isToday(run.finishedAt) ? "今日已生成" : translateStatus(run?.status) || "已有报告";

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>最新摘要</h2>
        <span className={`status ${run?.status || "success"}`}>{status}</span>
      </div>
      <div className="meta-grid">
        <Meta label="生成时间" value={formatDateTime(run?.finishedAt || report?.generatedAt)} />
        <Meta label="扫描信息源" value={String(run?.stats?.sourcesScanned ?? "未记录")} />
        <Meta label="抓取文章" value={String(run?.stats?.articlesFetched ?? "未记录")} />
        <Meta label="入选文章" value={String(run?.stats?.articlesSelected ?? report?.selectedCount ?? "未记录")} />
        <Meta label="语言" value={run?.paramsSnapshot.language === "en" ? "英文" : "中文"} />
        <Meta label="报告文件" value={report?.markdownPath || run?.output?.markdownPath || "未记录"} wide />
      </div>
      <div className="actions">
        <button onClick={onOpen} disabled={!report && !run?.output?.markdownPath}>打开最新报告</button>
        <button className="secondary" onClick={onReveal} disabled={!report && !run?.output?.markdownPath}>在文件夹中显示</button>
      </div>
    </section>
  );
}

function translateStatus(status?: string): string {
  const labels: Record<string, string> = {
    pending: "等待中",
    running: "生成中",
    success: "已完成",
    failed: "失败",
    cancelled: "已取消",
  };
  return status ? labels[status] || status : "";
}

function Meta({ label, value, wide }: { label: string; value: string; wide?: boolean }) {
  return (
    <div className={wide ? "meta-item wide" : "meta-item"}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
