import type { TopPick } from "../types/run";

type Props = {
  picks?: TopPick[];
};

export function TopPicksList({ picks }: Props) {
  const items = picks ?? [];
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Top Picks</h2>
        <span className="muted">{items.length ? `${items.length} items` : "Empty"}</span>
      </div>
      {items.length === 0 ? (
        <p className="muted">Top picks will appear after a successful digest run.</p>
      ) : (
        <ol className="top-picks">
          {items.slice(0, 3).map((pick, index) => (
            <li key={`${pick.title}-${index}`}>
              <strong>{pick.title}</strong>
              <span>{[pick.source, pick.publishedAt].filter(Boolean).join(" / ")}</span>
              {pick.reason && <p>{pick.reason}</p>}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
