import { marked } from "marked";
import type { MouseEvent } from "react";
import { useEffect, useMemo, useState } from "react";
import { copyText, openPath, readMarkdown, revealPath } from "../services/bridge";
import type { ReportRecord } from "../types/report";

type Props = {
  report?: ReportRecord;
};

export function MarkdownPreview({ report }: Props) {
  const [markdown, setMarkdown] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setMarkdown("");
    setError("");
    if (!report) return;
    if (report.markdown) {
      setMarkdown(report.markdown);
      return;
    }
    readMarkdown(report.markdownPath)
      .then(setMarkdown)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [report]);

  const html = useMemo(() => marked.parse(markdown, { async: false }), [markdown]);

  const openMarkdownLink = (event: MouseEvent<HTMLElement>) => {
    const target = event.target;
    if (!(target instanceof HTMLAnchorElement)) return;
    const href = target.href || target.getAttribute("href");
    if (!href) return;
    event.preventDefault();
    openPath(href);
  };

  if (!report) {
    return (
      <section className="preview empty">
        <h2>选择一份报告</h2>
        <p>Markdown 预览会显示在这里。</p>
      </section>
    );
  }

  return (
    <section className="preview">
      <div className="preview-toolbar">
        <div>
          <h2>{report.title}</h2>
          <span>{report.markdownPath}</span>
        </div>
        <div className="actions">
          <button className="secondary" onClick={() => copyText(markdown)}>复制 Markdown</button>
          <button className="secondary" disabled={report.markdownPath.startsWith("sample://")} onClick={() => openPath(report.markdownPath)}>打开文件</button>
          <button className="secondary" disabled={report.markdownPath.startsWith("sample://")} onClick={() => revealPath(report.markdownPath)}>在文件夹中显示</button>
        </div>
      </div>
      {error ? <p className="soft-error">{error}</p> : <article className="markdown" onClick={openMarkdownLink} dangerouslySetInnerHTML={{ __html: html }} />}
    </section>
  );
}
