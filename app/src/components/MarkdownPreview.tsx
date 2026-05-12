import { marked } from "marked";
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
    readMarkdown(report.markdownPath)
      .then(setMarkdown)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [report]);

  const html = useMemo(() => marked.parse(markdown, { async: false }), [markdown]);

  if (!report) {
    return (
      <section className="preview empty">
        <h2>Select a report</h2>
        <p>Markdown preview will appear here.</p>
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
          <button className="secondary" onClick={() => copyText(markdown)}>Copy Markdown</button>
          <button className="secondary" onClick={() => openPath(report.markdownPath)}>Open</button>
          <button className="secondary" onClick={() => revealPath(report.markdownPath)}>Reveal</button>
        </div>
      </div>
      {error ? <p className="soft-error">{error}</p> : <article className="markdown" dangerouslySetInnerHTML={{ __html: html }} />}
    </section>
  );
}
