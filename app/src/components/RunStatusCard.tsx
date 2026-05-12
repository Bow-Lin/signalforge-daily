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
    <section className="panel">
      <div className="panel-header">
        <h2>Recent Run</h2>
        <span className={`status ${run.status}`}>{run.status}</span>
      </div>
      <div className="meta-grid">
        <Meta label="Started" value={formatDateTime(run.startedAt)} />
        <Meta label="Finished" value={formatDateTime(run.finishedAt)} />
        <Meta label="Duration" value={formatDuration(run.durationMs)} />
        <Meta label="Current step" value={currentStep || run.status} />
      </div>
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
    </section>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="meta-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
