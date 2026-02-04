from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import ListedPost


_MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}

_DATE_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})\b"
)


class ClaudeBlogClient:
    def __init__(self, base_url: str = "https://claude.com/blog", timeout_s: int = 30) -> None:
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
        soup = BeautifulSoup(html, "html.parser")

        posts: list[ListedPost] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("/blog/") or href == "/blog":
                continue
            url = urljoin("https://claude.com", href)

            title = (a.get_text() or "").strip()
            if not title:
                continue

            date_dt = self._find_date_near(a)
            if date_dt is None:
                continue

            if date_dt >= since:
                posts.append(ListedPost(url=url, title=title, published_at=date_dt))

        dedup: dict[str, ListedPost] = {}
        for post in posts:
            existing = dedup.get(post.url)
            if existing is None or post.published_at > existing.published_at:
                dedup[post.url] = post
        return sorted(dedup.values(), key=lambda x: x.published_at, reverse=True)

    def fetch_html(self, url: str) -> str:
        resp = self.session.get(url, timeout=self.timeout_s)
        resp.raise_for_status()
        return resp.text

    def _find_date_near(self, node) -> Optional[datetime]:
        current = node
        for _ in range(4):
            text = " ".join(current.get_text(" ", strip=True).split())
            match = _DATE_RE.search(text)
            if match:
                month = _MONTHS[match.group(1)]
                day = int(match.group(2))
                year = int(match.group(3))
                return datetime(year, month, day, tzinfo=timezone.utc)
            parent = getattr(current, "parent", None)
            if parent is None:
                break
            current = parent
        return None
