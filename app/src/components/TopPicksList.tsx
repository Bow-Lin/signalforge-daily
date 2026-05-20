import type { TopPick } from "../types/run";
import { EmptyState } from "./ui";

type Props = {
  picks?: TopPick[];
  onReadReport?: () => void;
  onOpenOriginal?: (url: string) => void;
  onFavorite?: (pick: TopPick) => void;
  onFeedback?: (pick: TopPick, feedback: "useful" | "not_useful" | "hide_similar") => void;
};

export function TopPicksList({ picks, onReadReport, onOpenOriginal, onFavorite, onFeedback }: Props) {
  const items = picks ?? [];
  void onFavorite;
  return (
    <section className="top-picks-section">
      <div className="panel-header">
        <div>
          <h2>今日精选</h2>
          <p className="muted">优先读这几篇，就能抓住今天最重要的技术信号。</p>
        </div>
        <span className="muted">{items.length ? `${Math.min(items.length, 3)} 篇` : "暂无"}</span>
      </div>
      {items.length === 0 ? (
        <EmptyState title="还没有精选内容" description="生成摘要后，这里会展示最值得优先阅读的文章。" />
      ) : (
        <ol className="top-pick-cards">
          {items.slice(0, 3).map((pick, index) => (
            <li className="top-pick-card" key={`${pick.title}-${index}`}>
              <div className="pick-rank">{index + 1}</div>
              <div className="pick-body">
                <div className="pick-meta">
                  <span>{pick.source || "来源未记录"}</span>
                  <span>{inferTag(pick)}</span>
                  {pick.publishedAt && <span>{pick.publishedAt}</span>}
                </div>
                <h3>{pick.title}</h3>
                <p>{pick.reason || "打开完整报告查看摘要与上下文。"}</p>
                {pick.matchedTopics?.length ? <p className="matched-topics">匹配主题：{pick.matchedTopics.join(", ")}</p> : null}
                <div className="pick-actions">
                  <div className="read-actions">
                    <button className="secondary" onClick={onReadReport}>阅读全文</button>
                    <button className="secondary" disabled={!pick.url} onClick={() => pick.url && onOpenOriginal?.(pick.url)}>
                      打开原文
                    </button>
                  </div>
                  <div className="feedback-actions" aria-label="内容反馈">
                    <button className="feedback-button" onClick={() => onFeedback?.(pick, "useful")}>有用</button>
                    <button className="feedback-button" onClick={() => onFeedback?.(pick, "not_useful")}>不感兴趣</button>
                    <button className="feedback-button" onClick={() => onFeedback?.(pick, "hide_similar")}>隐藏类似</button>
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function inferTag(pick: TopPick): string {
  const text = `${pick.title} ${pick.reason || ""}`.toLowerCase();
  if (text.includes("agent") || text.includes("claude code")) return "Agent";
  if (text.includes("llm") || text.includes("model") || text.includes("模型")) return "LLM";
  if (text.includes("security") || text.includes("安全")) return "安全";
  if (text.includes("coding") || text.includes("code") || text.includes("编程")) return "Coding";
  return "技术信号";
}
