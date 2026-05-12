import type { RunRecord } from "../types/run";

type Props = {
  run?: RunRecord;
  onRetry: () => void;
  onSettings: () => void;
  onOpenLogs: () => void;
};

export function ErrorRecoveryCard({ run, onRetry, onSettings, onOpenLogs }: Props) {
  if (!run?.error) return null;

  return (
    <section className="panel danger-panel">
      <div className="panel-header">
        <h2>Digest failed</h2>
        <span className="status failed">{run.error.type}</span>
      </div>
      <h3>Reason</h3>
      <p>{run.error.message}</p>
      <h3>Possible fixes</h3>
      <ul className="fix-list">
        {run.error.suggestedActions.map((action) => (
          <li key={action}>{action}</li>
        ))}
      </ul>
      <div className="actions">
        <button onClick={onRetry}>Retry</button>
        <button className="secondary" onClick={onSettings}>Network Settings</button>
        <button className="secondary" onClick={onOpenLogs}>Open Logs</button>
      </div>
    </section>
  );
}
