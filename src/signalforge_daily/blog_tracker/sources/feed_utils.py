from __future__ import annotations

from datetime import datetime, timezone
import email.utils
from typing import Optional
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from .base import ListedPost


def discover_feed_url(html: str, base_url: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.find_all("link", href=True):
        rel = " ".join(link.get("rel", [])).lower()
        if "alternate" not in rel:
            continue
        link_type = (link.get("type") or "").lower()
        if "rss" in link_type or "atom" in link_type or "xml" in link_type:
            return urljoin(base_url, link["href"])
    return None


def parse_feed(xml_text: str) -> list[ListedPost]:
    root = ET.fromstring(xml_text)
    posts: list[ListedPost] = []

    if root.tag.endswith("feed"):
        posts.extend(_parse_atom(root))
    elif root.tag.endswith("rss"):
        posts.extend(_parse_rss(root))
    return posts


def _parse_atom(root: ET.Element) -> list[ListedPost]:
    ns = {"a": "http://www.w3.org/2005/Atom"}
    posts: list[ListedPost] = []
    for entry in root.findall("a:entry", ns):
        title = _text(entry.find("a:title", ns))
        link = entry.find("a:link", ns)
        href = link.get("href") if link is not None else ""
        published = _text(entry.find("a:published", ns)) or _text(entry.find("a:updated", ns))
        published_at = _parse_dt(published)
        if not href or not published_at:
            continue
        posts.append(ListedPost(url=href, title=title or href, published_at=published_at))
    return posts


def _parse_rss(root: ET.Element) -> list[ListedPost]:
    posts: list[ListedPost] = []
    for item in root.findall("./channel/item"):
        title = _text(item.find("title"))
        link = _text(item.find("link"))
        pub_date = _text(item.find("pubDate"))
        published_at = _parse_dt(pub_date)
        if not link or not published_at:
            continue
        posts.append(ListedPost(url=link, title=title or link, published_at=published_at))
    return posts


def _text(node: Optional[ET.Element]) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _parse_dt(value: str) -> Optional[datetime]:
    if not value:
        return None
    value = value.strip()
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        try:
            dt = email.utils.parsedate_to_datetime(value)
            if dt is None:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (TypeError, ValueError):
            return None
