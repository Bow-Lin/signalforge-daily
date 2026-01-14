from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
import xml.etree.ElementTree as ET

import requests


ARXIV_API = "http://export.arxiv.org/api/query"


@dataclass(frozen=True)
class ArxivEntry:
    arxiv_id: str
    title: str
    summary: str
    url: str
    published: datetime
    updated: datetime
    authors: list[str]


def _parse_dt(value: str) -> datetime:
    # arXiv uses ISO 8601 with Z.
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def _text(el: ET.Element | None) -> str:
    return "" if el is None or el.text is None else el.text.strip()


def fetch_arxiv(query: str, max_results: int = 50) -> list[ArxivEntry]:
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    resp = requests.get(ARXIV_API, params=params, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)

    ns = {"a": "http://www.w3.org/2005/Atom"}
    entries: list[ArxivEntry] = []
    for entry in root.findall("a:entry", ns):
        arxiv_id = _text(entry.find("a:id", ns))
        title = _text(entry.find("a:title", ns))
        summary = _text(entry.find("a:summary", ns))
        published = _parse_dt(_text(entry.find("a:published", ns)))
        updated = _parse_dt(_text(entry.find("a:updated", ns)))
        authors = [_text(a.find("a:name", ns)) for a in entry.findall("a:author", ns)]

        url = arxiv_id
        entries.append(
            ArxivEntry(
                arxiv_id=arxiv_id,
                title=title,
                summary=summary,
                url=url,
                published=published,
                updated=updated,
                authors=authors,
            )
        )
    return entries


def arxiv_pdf_url(arxiv_id: str) -> str:
    if "/abs/" in arxiv_id:
        return arxiv_id.replace("/abs/", "/pdf/") + ".pdf"
    if arxiv_id.endswith(".pdf"):
        return arxiv_id
    return arxiv_id + ".pdf"


def filter_by_date(
    entries: Iterable[ArxivEntry],
    start: datetime | None,
    end: datetime | None,
) -> list[ArxivEntry]:
    filtered = []
    for entry in entries:
        if start and entry.published < start:
            continue
        if end and entry.published > end:
            continue
        filtered.append(entry)
    return filtered
