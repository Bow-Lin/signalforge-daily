from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import ListedPost
from .date_utils import parse_date_text
from .feed_utils import discover_feed_url, parse_feed


class OpenAIDevBlogClient:
    def __init__(self, base_url: str = "https://developers.openai.com/blog/", timeout_s: int = 30) -> None:
        self.base_url = base_url
        self.timeout_s = timeout_s
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "blog-tracker/1.0 (+https://example.com)",
                "Accept": "text/html,application/xhtml+xml",
            }
        )

    def list_posts(self, since: datetime) -> list[ListedPost]:
        html = self.fetch_html(self.base_url)
        feed_url = discover_feed_url(html, self.base_url) or urljoin(self.base_url, "rss.xml")
        posts = self._try_feed(feed_url, since)
        if posts:
            return posts
        return self._list_from_html(html, since)

    def fetch_html(self, url: str) -> str:
        resp = self.session.get(url, timeout=self.timeout_s)
        resp.raise_for_status()
        return resp.text

    def _try_feed(self, feed_url: str, since: datetime) -> list[ListedPost]:
        try:
            feed_xml = self.fetch_html(feed_url)
        except requests.RequestException:
            return []
        posts = [p for p in parse_feed(feed_xml) if p.published_at >= since]
        dedup: dict[str, ListedPost] = {}
        for post in posts:
            existing = dedup.get(post.url)
            if existing is None or post.published_at > existing.published_at:
                dedup[post.url] = post
        return sorted(dedup.values(), key=lambda x: x.published_at, reverse=True)

    def _list_from_html(self, html: str, since: datetime) -> list[ListedPost]:
        soup = BeautifulSoup(html, "html.parser")
        posts: list[ListedPost] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("#"):
                continue
            if "/blog/" not in href:
                continue
            url = urljoin(self.base_url, href)
            title = self._extract_title(a)
            if not title:
                continue
            published_at = self._find_date_near(a)
            if not published_at or published_at < since:
                continue
            posts.append(ListedPost(url=url, title=title, published_at=published_at))
        return self._dedup(posts)

    def _extract_title(self, anchor) -> str:
        for tag in ("h1", "h2", "h3"):
            heading = anchor.find(tag)
            if heading and heading.get_text(strip=True):
                return heading.get_text(strip=True)
        text = (anchor.get_text() or "").strip()
        return text

    def _find_date_near(self, node) -> Optional[datetime]:
        current = node
        for _ in range(3):
            time_tag = current.find("time") if hasattr(current, "find") else None
            if time_tag is not None:
                dt = self._parse_time_tag(time_tag)
                if dt:
                    return dt
            text = " ".join(current.get_text(" ", strip=True).split())
            dt = parse_date_text(text)
            if dt:
                return dt
            parent = getattr(current, "parent", None)
            if parent is None:
                break
            current = parent
        return None

    def _parse_time_tag(self, time_tag) -> Optional[datetime]:
        dt_value = time_tag.get("datetime")
        if dt_value:
            try:
                if dt_value.endswith("Z"):
                    dt_value = dt_value[:-1] + "+00:00"
                dt = datetime.fromisoformat(dt_value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                pass
        return parse_date_text(time_tag.get_text(strip=True))

    def _dedup(self, posts: list[ListedPost]) -> list[ListedPost]:
        dedup: dict[str, ListedPost] = {}
        for post in posts:
            existing = dedup.get(post.url)
            if existing is None or post.published_at > existing.published_at:
                dedup[post.url] = post
        return sorted(dedup.values(), key=lambda x: x.published_at, reverse=True)
