import type { RunRecord } from "../types/run";

type Props = {
  run?: RunRecord;
};

export function FeedWarningsCard({ run }: Props) {
  const failures = run?.warnings?.feedFailures || [];
  if (run?.status !== "success" || failures.length === 0) return null;

  return (
    <section className="panel warning-panel stacked">
      <div>
        <strong>摘要已生成，但有信息源未成功读取。</strong>
        <p>{failures.length} 个信息源加载失败。本次摘要已使用成功读取的信息源生成。</p>
      </div>
      <details className="warning-details">
        <summary>查看失败信息源</summary>
        <ul>
          {failures.map((failure) => (
            <li key={`${failure.source}-${failure.reason}`}>
              <strong>{failure.source}</strong>
              <span>{failure.reason}</span>
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}
