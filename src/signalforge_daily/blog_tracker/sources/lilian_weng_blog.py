from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import ListedPost
from .date_utils import parse_date_text
from .feed_utils import discover_feed_url, parse_feed


_POST_DATE_RE = re.compile(r"/posts/(\d{4})-(\d{2})-(\d{2})")


class LilianWengBlogClient:
    def __init__(self, base_url: str = "https://lilianweng.github.io/", timeout_s: int = 30) -> None:
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
        feed_url = discover_feed_url(html, self.base_url) or urljoin(self.base_url, "feed.xml")
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
            if "/posts/" not in href:
                continue
            url = urljoin(self.base_url, href)
            title = (a.get_text() or "").strip()
            if not title:
                continue
            published_at = self._date_from_href(href) or self._find_date_near(a)
            if not published_at or published_at < since:
                continue
            posts.append(ListedPost(url=url, title=title, published_at=published_at))
        return self._dedup(posts)

    def _date_from_href(self, href: str) -> Optional[datetime]:
        match = _POST_DATE_RE.search(href)
        if not match:
            return None
        year, month, day = (int(v) for v in match.groups())
        return datetime(year, month, day, tzinfo=timezone.utc)

    def _find_date_near(self, node) -> Optional[datetime]:
        current = node
        for _ in range(3):
            text = " ".join(current.get_text(" ", strip=True).split())
            dt = parse_date_text(text)
            if dt:
                return dt
            parent = getattr(current, "parent", None)
            if parent is None:
                break
            current = parent
        return None

    def _dedup(self, posts: list[ListedPost]) -> list[ListedPost]:
        dedup: dict[str, ListedPost] = {}
        for post in posts:
            existing = dedup.get(post.url)
            if existing is None or post.published_at > existing.published_at:
                dedup[post.url] = post
        return sorted(dedup.values(), key=lambda x: x.published_at, reverse=True)
