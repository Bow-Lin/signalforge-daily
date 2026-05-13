from __future__ import annotations

import email.utils
import html
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Literal, TypeVar
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

from .blog_tracker.sources.claude_blog import ClaudeBlogClient
from .blog_tracker.sources.openai_blog import OpenAIDevBlogClient
from .digest_feeds import DEFAULT_BLOG_SOURCES, DEFAULT_RSS_FEEDS


logger = logging.getLogger(__name__)

CategoryId = Literal["ai-ml", "security", "engineering", "tools", "opinion", "other"]

CATEGORY_META: dict[CategoryId, tuple[str, str]] = {
    "ai-ml": ("🤖", "AI / ML"),
    "security": ("🔒", "安全"),
    "engineering": ("⚙️", "工程"),
    "tools": ("🛠", "工具 / 开源"),
    "opinion": ("💡", "观点 / 杂谈"),
    "other": ("📝", "其他"),
}

VALID_CATEGORIES = set(CATEGORY_META.keys())

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
T = TypeVar("T")


@dataclass(frozen=True)
class FeedSource:
    name: str
    xml_url: str
    source_type: Literal["rss", "openai_blog", "claude_blog"] = "rss"


@dataclass(frozen=True)
class Article:
    title: str
    link: str
    pub_date: datetime
    description: str
    source_name: str
    source_url: str


@dataclass(frozen=True)
class ScoreBreakdown:
    relevance: int
    quality: int
    timeliness: int


@dataclass(frozen=True)
class ScoredArticle:
    title: str
    link: str
    pub_date: datetime
    description: str
    source_name: str
    source_url: str
    score_breakdown: ScoreBreakdown
    category: CategoryId
    keywords: list[str]
    title_zh: str
    summary: str
    reason: str

    @property
    def total_score(self) -> int:
        return (
            int(self.score_breakdown.relevance)
            + int(self.score_breakdown.quality)
            + int(self.score_breakdown.timeliness)
        )


@dataclass(frozen=True)
class FetchStats:
    total_feeds: int
    success_feeds: int
    failed_feeds: int
    total_articles: int
    failures: dict[str, str]


@dataclass(frozen=True)
class DigestStats:
    total_feeds: int
    success_feeds: int
    total_articles: int
    filtered_articles: int
    hours: int


@dataclass(frozen=True)
class DigestRunResult:
    output_path: Path
    stats: DigestStats
    articles: list[ScoredArticle]
    highlights: str
    fetch_failures: dict[str, str]


class DigestAIClient:
    def __init__(
        self,
        *,
        iflow_key: str | None,
        iflow_base_url: str | None,
        iflow_model: str | None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> None:
        try:
            from .iflow import create_iflow_client, load_iflow_config
        except ModuleNotFoundError as exc:  # pragma: no cover - env specific
            raise RuntimeError(
                "Missing dependency for AI client. Install requirements via: pip install -r requirements.txt"
            ) from exc

        self._config = load_iflow_config(
            api_key=iflow_key,
            base_url=iflow_base_url,
            model=iflow_model,
        )
        self._client = create_iflow_client(self._config)
        self._temperature = temperature
        self._max_tokens = max_tokens

    @property
    def model_name(self) -> str:
        return self._config.model

    def call(self, prompt: str, *, temperature: float | None = None, max_tokens: int | None = None) -> str:
        response = self._client.chat.completions.create(
            model=self._config.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self._temperature if temperature is None else temperature,
            max_tokens=self._max_tokens if max_tokens is None else max_tokens,
        )
        text = _extract_response_text(response)
        if text:
            return text

        payload_preview = ""
        if hasattr(response, "model_dump"):
            try:
                payload_preview = json.dumps(response.model_dump(), ensure_ascii=False)[:500]
            except Exception:
                payload_preview = ""
        raise RuntimeError(
            "AI response has no usable text content"
            + (f"; preview={payload_preview}" if payload_preview else "")
        )


def _extract_text_from_content(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, dict):
        text_value = content.get("text")
        if isinstance(text_value, str):
            return text_value.strip()
        content_value = content.get("content")
        if isinstance(content_value, str):
            return content_value.strip()
        return ""
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                item_text = item.strip()
            elif isinstance(item, dict):
                raw = item.get("text")
                if not isinstance(raw, str):
                    raw = item.get("content") if isinstance(item.get("content"), str) else ""
                item_text = raw.strip() if isinstance(raw, str) else ""
            else:
                raw = getattr(item, "text", None)
                if not isinstance(raw, str):
                    raw = getattr(item, "content", None)
                item_text = raw.strip() if isinstance(raw, str) else ""
            if item_text:
                parts.append(item_text)
        return "\n".join(parts).strip()
    return ""


def _extract_text_from_choice(choice: object) -> str:
    if choice is None:
        return ""

    message = getattr(choice, "message", None)
    if message is None and isinstance(choice, dict):
        message = choice.get("message")

    candidates = [
        getattr(message, "content", None) if message is not None else None,
        message.get("content") if isinstance(message, dict) else None,
        getattr(choice, "text", None),
        choice.get("text") if isinstance(choice, dict) else None,
        getattr(message, "reasoning_content", None) if message is not None else None,
        message.get("reasoning_content") if isinstance(message, dict) else None,
    ]
    for candidate in candidates:
        text = _extract_text_from_content(candidate)
        if text:
            return text
    return ""


def _extract_response_text(response: object) -> str:
    choices = getattr(response, "choices", None)
    if isinstance(choices, list):
        for choice in choices:
            text = _extract_text_from_choice(choice)
            if text:
                return text

    payload: dict | None = None
    if hasattr(response, "model_dump"):
        try:
            dumped = response.model_dump()
            if isinstance(dumped, dict):
                payload = dumped
        except Exception:
            payload = None
    elif isinstance(response, dict):
        payload = response

    if not payload:
        return ""

    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    raw_choices = payload.get("choices")
    if isinstance(raw_choices, list):
        for choice in raw_choices:
            text = _extract_text_from_choice(choice)
            if text:
                return text

    return ""


def load_default_feed_sources() -> list[FeedSource]:
    rss_sources = [FeedSource(name=name, xml_url=xml_url) for name, xml_url in DEFAULT_RSS_FEEDS]
    blog_sources = [
        FeedSource(name=name, xml_url=xml_url, source_type=source_type)
        for name, xml_url, source_type in DEFAULT_BLOG_SOURCES
    ]
    return rss_sources + blog_sources


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _clean_text(value: str) -> str:
    if not value:
        return ""
    return " ".join(html.unescape(value).split()).strip()


def _strip_html(value: str) -> str:
    if not value:
        return ""
    soup = BeautifulSoup(value, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return _clean_text(soup.get_text(" ", strip=True))


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass
    try:
        dt = email.utils.parsedate_to_datetime(value)
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


def _child_text(node: ET.Element, names: set[str]) -> str:
    for child in list(node):
        if _local_name(child.tag) in names:
            return _clean_text("".join(child.itertext()))
    return ""


def _entry_link(entry: ET.Element) -> str:
    fallback = ""
    for child in list(entry):
        if _local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href", "").strip()
        if not href:
            continue
        rel = child.attrib.get("rel", "alternate").strip().lower() or "alternate"
        if rel == "alternate":
            return href
        if not fallback:
            fallback = href
    return fallback


def parse_feed_items(xml_text: str, source_name: str, source_url: str) -> list[Article]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    root_name = _local_name(root.tag).lower()
    items: list[Article] = []

    if root_name in {"rss", "rdf"}:
        for node in root.iter():
            if _local_name(node.tag) != "item":
                continue
            title = _child_text(node, {"title"})
            link = _child_text(node, {"link", "guid"})
            published = _child_text(node, {"pubDate", "published", "updated", "date"})
            description = _child_text(node, {"description", "summary", "encoded", "content"})
            pub_date = _parse_datetime(published)
            if not link or not pub_date:
                continue
            items.append(
                Article(
                    title=title or link,
                    link=link,
                    pub_date=pub_date,
                    description=_strip_html(description) or title or link,
                    source_name=source_name,
                    source_url=source_url,
                )
            )

    elif root_name == "feed":
        for node in root.iter():
            if _local_name(node.tag) != "entry":
                continue
            title = _child_text(node, {"title"})
            link = _entry_link(node)
            published = _child_text(node, {"published", "updated"})
            description = _child_text(node, {"summary", "content"})
            pub_date = _parse_datetime(published)
            if not link or not pub_date:
                continue
            items.append(
                Article(
                    title=title or link,
                    link=link,
                    pub_date=pub_date,
                    description=_strip_html(description) or title or link,
                    source_name=source_name,
                    source_url=source_url,
                )
            )

    return _dedupe_articles(items)


def _dedupe_articles(items: Iterable[Article]) -> list[Article]:
    dedup: dict[str, Article] = {}
    for item in items:
        current = dedup.get(item.link)
        if current is None or item.pub_date > current.pub_date:
            dedup[item.link] = item
    return sorted(dedup.values(), key=lambda it: it.pub_date, reverse=True)


def _build_blog_client(source: FeedSource, timeout_s: int):
    if source.source_type == "openai_blog":
        return OpenAIDevBlogClient(base_url=source.xml_url, timeout_s=timeout_s)
    if source.source_type == "claude_blog":
        return ClaudeBlogClient(base_url=source.xml_url, timeout_s=timeout_s)
    raise ValueError(f"unsupported blog source type: {source.source_type}")


def _extract_blog_description(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    selectors = [
        "article",
        "main",
        "[role='main']",
    ]
    container = None
    for selector in selectors:
        container = soup.select_one(selector)
        if container is not None:
            break
    if container is None:
        container = soup.body or soup

    parts: list[str] = []
    for node in container.find_all(["p", "li"]):
        text = _clean_text(node.get_text(" ", strip=True))
        if text:
            parts.append(text)
        if len(" ".join(parts)) >= 1200:
            break

    if not parts:
        fallback_text = _clean_text(container.get_text(" ", strip=True))
        return fallback_text[:1200]
    return " ".join(parts)[:1200]


def _fetch_blog_source(
    source: FeedSource,
    timeout_s: int,
    *,
    since: datetime | None,
) -> list[Article]:
    client = _build_blog_client(source, timeout_s)
    effective_since = since or (datetime.now(timezone.utc) - timedelta(days=180))
    posts = client.list_posts(effective_since)

    articles: list[Article] = []
    for post in posts:
        description = post.title
        try:
            html_text = client.fetch_html(post.url)
        except Exception as exc:
            logger.warning("[digest] failed to fetch blog post body %s: %s", post.url, exc)
        else:
            description = _extract_blog_description(html_text) or post.title

        articles.append(
            Article(
                title=post.title,
                link=post.url,
                pub_date=post.published_at,
                description=description,
                source_name=source.name,
                source_url=source.xml_url,
            )
        )
    return _dedupe_articles(articles)


def _fetch_feed(source: FeedSource, timeout_s: int, *, since: datetime | None = None) -> list[Article]:
    if source.source_type != "rss":
        return _fetch_blog_source(source, timeout_s, since=since)

    headers = {
        "User-Agent": "signalforge-daily-digest/1.0 (+https://example.com)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    }
    resp = requests.get(source.xml_url, headers=headers, timeout=timeout_s)
    resp.raise_for_status()
    return parse_feed_items(resp.text, source_name=source.name, source_url=source.xml_url)


def fetch_all_feeds(
    feeds: list[FeedSource],
    *,
    timeout_s: int = 15,
    concurrency: int = 10,
    since: datetime | None = None,
) -> tuple[list[Article], FetchStats]:
    all_articles: list[Article] = []
    failures: dict[str, str] = {}
    success_feeds = 0
    processed = 0

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = {
            executor.submit(_fetch_feed, feed, timeout_s, since=since): feed for feed in feeds
        }
        total = len(futures)
        for future in as_completed(futures):
            feed = futures[future]
            processed += 1
            try:
                items = future.result()
            except Exception as exc:
                reason = str(exc).strip() or exc.__class__.__name__
                failures[feed.name] = reason
                logger.warning("[digest] ✗ %s: %s", feed.name, reason)
                items = []

            if items:
                success_feeds += 1
                all_articles.extend(items)
            else:
                failures.setdefault(feed.name, failures.get(feed.name, "empty feed"))

            logger.info(
                "[digest] Progress: %s/%s feeds processed (%s ok, %s failed)",
                processed,
                total,
                success_feeds,
                processed - success_feeds,
            )

    deduped = _dedupe_articles(all_articles)
    stats = FetchStats(
        total_feeds=len(feeds),
        success_feeds=success_feeds,
        failed_feeds=len(feeds) - success_feeds,
        total_articles=len(deduped),
        failures=failures,
    )
    return deduped, stats


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    match = _JSON_BLOCK_RE.search(stripped)
    if match:
        return match.group(1).strip()
    return stripped


def parse_json_response(text: str) -> dict:
    cleaned = _strip_code_fence(text)
    if not cleaned:
        return {}
    try:
        payload = json.loads(cleaned)
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        payload = json.loads(cleaned[start : end + 1])
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {}


def _chunked(items: list[T], size: int) -> list[list[T]]:
    if size <= 0:
        size = 1
    return [items[i : i + size] for i in range(0, len(items), size)]


def _call_with_retry(ai_client: DigestAIClient, prompt: str, *, retries: int) -> str:
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return ai_client.call(prompt)
        except Exception as exc:  # pragma: no cover - network/API behavior
            last_err = exc
            if attempt >= retries:
                break
            wait_s = min(20, 2 * (attempt + 1))
            logger.warning("[digest] AI call failed (attempt=%s/%s): %s", attempt + 1, retries + 1, exc)
            time.sleep(wait_s)
    if last_err is not None:
        raise last_err
    raise RuntimeError("unknown AI call error")


def build_scoring_prompt(batch: list[tuple[int, Article]]) -> str:
    blocks = []
    for idx, article in batch:
        blocks.append(
            f"Index {idx}: [{article.source_name}] {article.title}\n"
            f"{article.description[:300]}"
        )

    article_text = "\n\n---\n\n".join(blocks)
    return (
        "你是技术内容编辑，正在为每日技术摘要筛选文章。\n\n"
        "请对每篇文章给出：\n"
        "1) relevance: 对技术从业者的价值（1-10）\n"
        "2) quality: 内容质量与深度（1-10）\n"
        "3) timeliness: 时效性（1-10）\n"
        "4) category: 必须是 ai-ml/security/engineering/tools/opinion/other 之一\n"
        "5) keywords: 2-4 个关键词\n\n"
        "文章列表：\n"
        f"{article_text}\n\n"
        "仅返回 JSON，格式如下：\n"
        "{\n"
        "  \"results\": [\n"
        "    {\n"
        "      \"index\": 0,\n"
        "      \"relevance\": 8,\n"
        "      \"quality\": 7,\n"
        "      \"timeliness\": 9,\n"
        "      \"category\": \"engineering\",\n"
        "      \"keywords\": [\"rust\", \"compiler\", \"performance\"]\n"
        "    }\n"
        "  ]\n"
        "}"
    )


def score_articles_with_ai(
    articles: list[Article],
    ai_client: DigestAIClient,
    *,
    batch_size: int = 10,
    retries: int = 1,
) -> dict[int, tuple[ScoreBreakdown, CategoryId, list[str]]]:
    result: dict[int, tuple[ScoreBreakdown, CategoryId, list[str]]] = {}
    indexed = list(enumerate(articles))
    batches = _chunked(indexed, batch_size)
    logger.info("[digest] AI scoring: %s articles in %s batches", len(articles), len(batches))

    for batch_index, batch in enumerate(batches, start=1):
        try:
            prompt = build_scoring_prompt(batch)
            payload = parse_json_response(_call_with_retry(ai_client, prompt, retries=retries))
            rows = payload.get("results") if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                rows = []

            for row in rows:
                if not isinstance(row, dict):
                    continue
                idx = row.get("index")
                if not isinstance(idx, int):
                    continue
                relevance = int(round(float(row.get("relevance", 5))))
                quality = int(round(float(row.get("quality", 5))))
                timeliness = int(round(float(row.get("timeliness", 5))))
                relevance = max(1, min(10, relevance))
                quality = max(1, min(10, quality))
                timeliness = max(1, min(10, timeliness))
                category_raw = str(row.get("category", "other")).strip()
                category: CategoryId = (
                    category_raw if category_raw in VALID_CATEGORIES else "other"
                )  # type: ignore[assignment]
                keywords_raw = row.get("keywords", [])
                keywords: list[str] = []
                if isinstance(keywords_raw, list):
                    for item in keywords_raw[:4]:
                        text = _clean_text(str(item))
                        if text:
                            keywords.append(text)

                result[idx] = (
                    ScoreBreakdown(
                        relevance=relevance,
                        quality=quality,
                        timeliness=timeliness,
                    ),
                    category,
                    keywords,
                )

        except Exception as exc:
            logger.warning("[digest] scoring batch failed: %s", exc)

        for idx, _article in batch:
            if idx not in result:
                result[idx] = (ScoreBreakdown(5, 5, 5), "other", [])

        logger.info("[digest] Scoring progress: %s/%s batches", batch_index, len(batches))

    return result


def build_summary_prompt(batch: list[tuple[int, Article]], lang: Literal["zh", "en"]) -> str:
    blocks = []
    for idx, article in batch:
        blocks.append(
            f"Index {idx}: [{article.source_name}] {article.title}\n"
            f"URL: {article.link}\n"
            f"{article.description[:800]}"
        )
    article_text = "\n\n---\n\n".join(blocks)
    lang_instruction = (
        "请用中文写摘要、推荐理由和标题翻译。"
        if lang == "zh"
        else "Write summaries, reasons, and title translation in English."
    )
    return (
        "你是技术内容摘要编辑。请对每篇文章输出三个字段：\n"
        "1) titleZh: 标题翻译（若原文中文可保持不变）\n"
        "2) summary: 4-6 句结构化摘要，覆盖核心问题、关键观点、结论\n"
        "3) reason: 1 句推荐理由，强调为什么值得读\n\n"
        f"{lang_instruction}\n\n"
        "文章列表：\n"
        f"{article_text}\n\n"
        "仅返回 JSON：\n"
        "{\n"
        "  \"results\": [\n"
        "    {\n"
        "      \"index\": 0,\n"
        "      \"titleZh\": \"...\",\n"
        "      \"summary\": \"...\",\n"
        "      \"reason\": \"...\"\n"
        "    }\n"
        "  ]\n"
        "}"
    )


def summarize_articles(
    articles: list[Article],
    ai_client: DigestAIClient,
    *,
    lang: Literal["zh", "en"] = "zh",
    batch_size: int = 10,
    retries: int = 1,
) -> dict[int, tuple[str, str, str]]:
    result: dict[int, tuple[str, str, str]] = {}
    indexed = list(enumerate(articles))
    batches = _chunked(indexed, batch_size)
    logger.info("[digest] Generating summaries: %s articles in %s batches", len(articles), len(batches))

    for batch_index, batch in enumerate(batches, start=1):
        try:
            prompt = build_summary_prompt(batch, lang)
            payload = parse_json_response(_call_with_retry(ai_client, prompt, retries=retries))
            rows = payload.get("results") if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                rows = []

            for row in rows:
                if not isinstance(row, dict):
                    continue
                idx = row.get("index")
                if not isinstance(idx, int):
                    continue
                title_zh = _clean_text(str(row.get("titleZh", "")))
                summary = _clean_text(str(row.get("summary", "")))
                reason = _clean_text(str(row.get("reason", "")))
                result[idx] = (title_zh, summary, reason)

        except Exception as exc:
            logger.warning("[digest] summary batch failed: %s", exc)

        for idx, article in batch:
            if idx not in result:
                fallback_summary = article.description[:220] or article.title
                result[idx] = (article.title, fallback_summary, "")

        logger.info("[digest] Summary progress: %s/%s batches", batch_index, len(batches))

    return result


def generate_highlights(
    articles: list[ScoredArticle],
    ai_client: DigestAIClient,
    *,
    lang: Literal["zh", "en"] = "zh",
    retries: int = 1,
) -> str:
    if not articles:
        return ""
    article_list = "\n".join(
        f"{idx + 1}. [{article.category}] {article.title_zh or article.title} - {article.summary[:100]}"
        for idx, article in enumerate(articles[:10])
    )
    lang_note = "用中文回答。" if lang == "zh" else "Write in English."
    prompt = (
        "根据以下今日精选技术文章，提炼 2-3 个宏观趋势，写 3-5 句话的今日看点。\n"
        "不要逐篇复述，强调趋势和关联。\n"
        f"{lang_note}\n\n"
        f"{article_list}\n\n"
        "只返回纯文本。"
    )
    try:
        return _clean_text(_call_with_retry(ai_client, prompt, retries=retries))
    except Exception as exc:
        logger.warning("[digest] highlights generation failed: %s", exc)
        return ""


def humanize_time(pub_date: datetime) -> str:
    delta = datetime.now(timezone.utc) - pub_date.astimezone(timezone.utc)
    minutes = int(delta.total_seconds() // 60)
    if minutes < 1:
        return "刚刚"
    if minutes < 60:
        return f"{minutes} 分钟前"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} 小时前"
    days = hours // 24
    if days < 7:
        return f"{days} 天前"
    return pub_date.strftime("%Y-%m-%d")


def _top_keywords(articles: list[ScoredArticle], limit: int) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for article in articles:
        for kw in article.keywords:
            key = _clean_text(kw).lower()
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]


def generate_keyword_bar_chart(articles: list[ScoredArticle]) -> str:
    top = _top_keywords(articles, 12)
    if not top:
        return ""
    labels: list[str] = []
    for label, _ in top:
        escaped = label.replace('"', '\\"')
        labels.append(f'"{escaped}"')
    values = ", ".join(str(value) for _, value in top)
    max_val = max(value for _, value in top)
    return (
        "```mermaid\n"
        "xychart-beta horizontal\n"
        "    title \"高频关键词\"\n"
        f"    x-axis [{', '.join(labels)}]\n"
        f"    y-axis \"出现次数\" 0 --> {max_val + 2}\n"
        f"    bar [{values}]\n"
        "```\n"
    )


def generate_category_pie_chart(articles: list[ScoredArticle]) -> str:
    counts: dict[CategoryId, int] = {}
    for article in articles:
        counts[article.category] = counts.get(article.category, 0) + 1
    if not counts:
        return ""
    lines = ["```mermaid", "pie showData", '    title "文章分类分布"']
    for category, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        emoji, label = CATEGORY_META[category]
        lines.append(f'    "{emoji} {label}" : {count}')
    lines.append("```")
    return "\n".join(lines) + "\n"


def generate_ascii_bar_chart(articles: list[ScoredArticle]) -> str:
    top = _top_keywords(articles, 10)
    if not top:
        return ""
    max_val = max(value for _, value in top)
    max_label_len = max(len(label) for label, _ in top)
    width = 20
    lines = ["```"]
    for label, value in top:
        bar_len = max(1, round((value / max_val) * width))
        bar = "#" * bar_len + "." * (width - bar_len)
        lines.append(f"{label.ljust(max_label_len)} | {bar} {value}")
    lines.append("```")
    return "\n".join(lines) + "\n"


def generate_tag_cloud(articles: list[ScoredArticle]) -> str:
    top = _top_keywords(articles, 20)
    if not top:
        return ""
    words: list[str] = []
    for idx, (word, count) in enumerate(top):
        if idx < 3:
            words.append(f"**{word}**({count})")
        else:
            words.append(f"{word}({count})")
    return " · ".join(words)


def generate_digest_report(articles: list[ScoredArticle], highlights: str, stats: DigestStats) -> str:
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    report = f"# 📰 AI 博客每日精选 — {date_str}\n\n"
    report += f"> 基于 {stats.total_feeds} 个技术博客源，AI 精选 Top {len(articles)}\n\n"

    if highlights:
        report += "## 📝 今日看点\n\n"
        report += f"{highlights}\n\n"
        report += "---\n\n"

    if len(articles) >= 3:
        report += "## 🏆 今日必读\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for idx, article in enumerate(articles[:3]):
            emoji, label = CATEGORY_META[article.category]
            report += f"{medals[idx]} **{article.title_zh or article.title}**\n\n"
            report += (
                f"[{article.title}]({article.link}) — {article.source_name} · "
                f"{humanize_time(article.pub_date)} · {emoji} {label}\n\n"
            )
            report += f"> {article.summary}\n\n"
            if article.reason:
                report += f"💡 **为什么值得读**: {article.reason}\n\n"
            if article.keywords:
                report += f"🏷️ {', '.join(article.keywords)}\n\n"
        report += "---\n\n"

    report += "## 📊 数据概览\n\n"
    report += "| 扫描源 | 抓取文章 | 时间范围 | 精选 |\n"
    report += "|:---:|:---:|:---:|:---:|\n"
    report += (
        f"| {stats.success_feeds}/{stats.total_feeds} | {stats.total_articles} 篇 → {stats.filtered_articles} 篇 "
        f"| {stats.hours}h | **{len(articles)} 篇** |\n\n"
    )

    pie_chart = generate_category_pie_chart(articles)
    if pie_chart:
        report += f"### 分类分布\n\n{pie_chart}\n"

    keyword_chart = generate_keyword_bar_chart(articles)
    if keyword_chart:
        report += f"### 高频关键词\n\n{keyword_chart}\n"

    ascii_chart = generate_ascii_bar_chart(articles)
    if ascii_chart:
        report += f"<details>\n<summary>📈 纯文本关键词图</summary>\n\n{ascii_chart}\n</details>\n\n"

    tag_cloud = generate_tag_cloud(articles)
    if tag_cloud:
        report += f"### 🏷️ 话题标签\n\n{tag_cloud}\n\n"

    report += "---\n\n"

    grouped: dict[CategoryId, list[ScoredArticle]] = {}
    for article in articles:
        grouped.setdefault(article.category, []).append(article)

    global_index = 0
    for category, entries in sorted(grouped.items(), key=lambda item: len(item[1]), reverse=True):
        emoji, label = CATEGORY_META[category]
        report += f"## {emoji} {label}\n\n"
        for article in entries:
            global_index += 1
            report += f"### {global_index}. {article.title_zh or article.title}\n\n"
            report += (
                f"[{article.title}]({article.link}) — **{article.source_name}** · "
                f"{humanize_time(article.pub_date)} · ⭐ {article.total_score}/30\n\n"
            )
            report += f"> {article.summary}\n\n"
            if article.keywords:
                report += f"🏷️ {', '.join(article.keywords)}\n\n"
            report += "---\n\n"

    report += (
        f"*生成于 {date_str} {now.strftime('%H:%M')} UTC | 扫描 {stats.success_feeds} 源 "
        f"→ 获取 {stats.total_articles} 篇 → 精选 {len(articles)} 篇*\n"
    )
    return report


def _ensure_output_path(path: str | None) -> Path:
    if path:
        resolved = Path(path)
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        resolved = Path(f"./output/digest-{date_str}.md")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def run_digest(
    *,
    hours: int = 48,
    top_n: int = 15,
    lang: Literal["zh", "en"] = "zh",
    output_path: str | None = None,
    iflow_key: str | None = None,
    iflow_base_url: str | None = None,
    iflow_model: str | None = None,
    feed_timeout_s: int = 15,
    feed_concurrency: int = 10,
    ai_batch_size: int = 10,
    ai_retries: int = 1,
    max_ai_articles: int = 120,
    feeds: list[FeedSource] | None = None,
) -> DigestRunResult:
    if hours <= 0:
        raise ValueError("hours must be > 0")
    if top_n <= 0:
        raise ValueError("top_n must be > 0")

    sources = feeds or load_default_feed_sources()
    logger.info("[digest] Step 1/5: Fetching %s digest sources...", len(sources))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    all_articles, fetch_stats = fetch_all_feeds(
        sources,
        timeout_s=feed_timeout_s,
        concurrency=feed_concurrency,
        since=cutoff,
    )

    if not all_articles:
        raise RuntimeError("No articles fetched from any feed")

    logger.info("[digest] Step 2/5: Filtering by time range (%s hours)...", hours)
    recent_articles = [it for it in all_articles if it.pub_date.astimezone(timezone.utc) > cutoff]

    if not recent_articles:
        raise RuntimeError(f"No articles found within last {hours} hours")

    recent_articles.sort(key=lambda it: it.pub_date, reverse=True)
    if len(recent_articles) > max_ai_articles:
        logger.info(
            "[digest] Capping AI candidates to %s (from %s) for cost/latency control",
            max_ai_articles,
            len(recent_articles),
        )
        recent_articles = recent_articles[:max_ai_articles]

    ai_client = DigestAIClient(
        iflow_key=iflow_key,
        iflow_base_url=iflow_base_url,
        iflow_model=iflow_model,
    )

    logger.info("[digest] Step 3/5: AI scoring %s articles...", len(recent_articles))
    scoring = score_articles_with_ai(
        recent_articles,
        ai_client,
        batch_size=ai_batch_size,
        retries=ai_retries,
    )

    scored_rows: list[tuple[Article, ScoreBreakdown, CategoryId, list[str]]] = []
    for idx, article in enumerate(recent_articles):
        breakdown, category, keywords = scoring.get(idx, (ScoreBreakdown(5, 5, 5), "other", []))
        scored_rows.append((article, breakdown, category, keywords))

    scored_rows.sort(
        key=lambda row: (
            row[1].relevance + row[1].quality + row[1].timeliness,
            row[0].pub_date,
        ),
        reverse=True,
    )
    top_rows = scored_rows[:top_n]

    logger.info("[digest] Step 4/5: Generating AI summaries for top %s...", len(top_rows))
    top_articles = [row[0] for row in top_rows]
    summaries = summarize_articles(
        top_articles,
        ai_client,
        lang=lang,
        batch_size=ai_batch_size,
        retries=ai_retries,
    )

    final_articles: list[ScoredArticle] = []
    for idx, (article, breakdown, category, keywords) in enumerate(top_rows):
        title_zh, summary, reason = summaries.get(idx, (article.title, article.description[:220], ""))
        final_articles.append(
            ScoredArticle(
                title=article.title,
                link=article.link,
                pub_date=article.pub_date,
                description=article.description,
                source_name=article.source_name,
                source_url=article.source_url,
                score_breakdown=breakdown,
                category=category,
                keywords=keywords,
                title_zh=title_zh or article.title,
                summary=summary or article.description[:220] or article.title,
                reason=reason,
            )
        )

    logger.info("[digest] Step 5/5: Generating highlights...")
    highlights = generate_highlights(final_articles, ai_client, lang=lang, retries=ai_retries)

    stats = DigestStats(
        total_feeds=fetch_stats.total_feeds,
        success_feeds=fetch_stats.success_feeds,
        total_articles=fetch_stats.total_articles,
        filtered_articles=len(recent_articles),
        hours=hours,
    )

    report = generate_digest_report(final_articles, highlights, stats)
    out_path = _ensure_output_path(output_path)
    out_path.write_text(report, encoding="utf-8")

    return DigestRunResult(
        output_path=out_path,
        stats=stats,
        articles=final_articles,
        highlights=highlights,
        fetch_failures=fetch_stats.failures,
    )
