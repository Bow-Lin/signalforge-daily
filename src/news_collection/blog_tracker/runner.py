from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from ..iflow import create_iflow_client, load_iflow_config
from ..telemetry import flush, log_generation, log_span, start_trace, update_trace_name
from .sources.claude_blog import ClaudeBlogClient
from .sources.lilian_weng_blog import LilianWengBlogClient
from .sources.openai_blog import OpenAIDevBlogClient
from .storage import Storage


logger = logging.getLogger(__name__)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower())
    return slug.strip("-") or "post"


def _default_blog_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "blog"


def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _build_summary_prompt(title: str, url: str, text: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                "You are a concise technical reader. "
                "Return a single paragraph summary in Chinese, about 200 Chinese characters. "
                "Do not use bullet points. Avoid speculation."
            ),
        },
        {
            "role": "user",
            "content": f"Title: {title}\nURL: {url}\nCONTENT:\n{text}",
        },
    ]


def _safe_get_message_content(response) -> str:
    try:
        return response.choices[0].message.content or ""
    except (AttributeError, IndexError):
        return ""


def _extract_usage(response) -> dict | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    if isinstance(usage, dict):
        return usage
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    return usage.__dict__ if hasattr(usage, "__dict__") else None


def _safe_short(value: str, max_chars: int = 200) -> str:
    if not value:
        return ""
    return value[:max_chars]


@dataclass
class SyncResult:
    blog_url: str
    since: str
    now: str
    new_or_updated: int
    saved: list[str]
    summaries: dict[str, str]


class BlogTracker:
    def __init__(
        self,
        storage: Storage,
        data_dir: str | None = None,
        iflow_key: str | None = None,
        iflow_base_url: str | None = None,
        iflow_model: str | None = None,
        session_id: str | None = None,
        defer_last_run_at: bool = False,
        summary_max_input_chars: int = 8000,
        summary_max_tokens: int = 400,
    ) -> None:
        self.storage = storage
        self.data_dir = Path(data_dir) if data_dir else _default_blog_dir()
        self.iflow_key = iflow_key
        self.iflow_base_url = iflow_base_url
        self.iflow_model = iflow_model
        self.session_id = session_id
        self.defer_last_run_at = defer_last_run_at
        self.summary_max_input_chars = summary_max_input_chars
        self.summary_max_tokens = summary_max_tokens
        self._llm_client = None
        self._llm_config = None

    def sync_claude_blog(self, blog_url: str = "https://claude.com/blog") -> SyncResult:
        client = ClaudeBlogClient(base_url=blog_url)
        return self._sync_client(client, blog_url, "Claude Blog")

    def sync_lilian_weng_blog(
        self, blog_url: str = "https://lilianweng.github.io/"
    ) -> SyncResult:
        client = LilianWengBlogClient(base_url=blog_url)
        return self._sync_client(client, blog_url, "Lilian Weng Blog")

    def sync_openai_blog(
        self, blog_url: str = "https://developers.openai.com/blog/"
    ) -> SyncResult:
        client = OpenAIDevBlogClient(base_url=blog_url)
        return self._sync_client(client, blog_url, "OpenAI Developers Blog")

    def _ensure_llm(self):
        if self._llm_client and self._llm_config:
            return self._llm_client, self._llm_config
        config = load_iflow_config(
            api_key=self.iflow_key,
            base_url=self.iflow_base_url,
            model=self.iflow_model,
        )
        self._llm_config = config
        self._llm_client = create_iflow_client(config)
        return self._llm_client, self._llm_config

    def _summarize_post(self, title: str, url: str, text: str, trace_id: str | None) -> str:
        if not text:
            return ""
        try:
            client, config = self._ensure_llm()
        except Exception as exc:
            logger.warning(
                "summary skipped title=%s url=%s err=%s",
                _safe_short(title),
                url,
                exc,
            )
            return ""
        snippet = _truncate_text(text, self.summary_max_input_chars)
        messages = _build_summary_prompt(title, url, snippet)
        try:
            response = client.chat.completions.create(
                model=config.model,
                messages=messages,
                temperature=0.2,
                max_tokens=self.summary_max_tokens,
            )
        except Exception as exc:
            logger.warning(
                "summary failed title=%s url=%s err=%s",
                _safe_short(title),
                url,
                exc,
            )
            return ""
        summary = _safe_get_message_content(response).strip()
        log_generation(
            trace_id=trace_id,
            name="blog_summary",
            model=config.model,
            input={
                "title": _safe_short(title),
                "url": url,
                "content_prefix": _safe_short(snippet, 500),
            },
            output={"summary": summary},
            usage=_extract_usage(response),
        )
        return summary

    def _sync_client(self, client, blog_url: str, name: str) -> SyncResult:
        now = datetime.now(timezone.utc)

        self.storage.upsert_source(url=blog_url, name=name)
        sources = [s for s in self.storage.list_sources() if s.url == blog_url]
        if not sources:
            raise RuntimeError(f"source not found after upsert: {blog_url}")
        blog = sources[0]

        last_run_at = self.storage.get_last_run_at()
        if last_run_at:
            try:
                since = datetime.fromisoformat(last_run_at)
            except ValueError:
                logger.warning("invalid last_run_at=%s; fallback to 180 days", last_run_at)
                since = now - timedelta(days=180)
            else:
                if since.tzinfo is None:
                    since = since.replace(tzinfo=timezone.utc)
        else:
            since = now - timedelta(days=180)

        trace_id = start_trace(
            name="blog_sync",
            input={"blog_url": blog_url, "since": since.isoformat(), "source_name": name},
            session_id=self.session_id,
        )

        listed = client.list_posts(since=since)
        log_span(
            trace_id=trace_id,
            name="list_posts",
            input={"since": since.isoformat()},
            output={"count": len(listed)},
            as_type="tool",
        )

        saved_urls: list[str] = []
        summaries: dict[str, str] = {}
        changed = 0

        blog_dir = self.data_dir / f"blog_{blog.id}"
        blog_dir.mkdir(parents=True, exist_ok=True)

        for item in listed:
            try:
                html = client.fetch_html(item.url)
                log_span(
                    trace_id=trace_id,
                    name="fetch_post",
                    input={"url": item.url},
                    output={"chars": len(html)},
                    as_type="tool",
                )
            except Exception as exc:
                log_span(
                    trace_id=trace_id,
                    name="fetch_post",
                    input={"url": item.url},
                    output={"chars": 0},
                    error=str(exc),
                    as_type="tool",
                )
                continue
            text = _extract_text(html)
            content_hash = _sha256(text)

            slug = _slugify(item.url.rstrip("/").split("/")[-1])
            date_prefix = item.published_at.strftime("%Y-%m-%d")
            html_path = blog_dir / f"{date_prefix}_{slug}.html"
            txt_path = blog_dir / f"{date_prefix}_{slug}.txt"

            existing_hash = None
            if txt_path.exists():
                try:
                    existing_text = txt_path.read_text(encoding="utf-8")
                    existing_hash = _sha256(existing_text)
                except OSError:
                    existing_hash = None
            if existing_hash == content_hash:
                continue

            html_path.write_text(html, encoding="utf-8")
            txt_path.write_text(text, encoding="utf-8")
            saved_urls.append(item.url)
            changed += 1

            summary = self._summarize_post(item.title, item.url, text, trace_id)
            if summary:
                summaries[item.url] = summary

        update_trace_name(
            trace_id,
            name="blog_sync",
            session_id=self.session_id,
            input={
                "blog_url": blog_url,
                "since": since.isoformat(),
                "new_or_updated": changed,
            },
        )
        flush()
        if not self.defer_last_run_at:
            self.storage.update_last_run_at(now.isoformat())

        return SyncResult(
            blog_url=blog_url,
            since=since.isoformat(),
            now=now.isoformat(),
            new_or_updated=changed,
            saved=saved_urls,
            summaries=summaries,
        )
