from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional
from urllib.parse import urlencode

import requests
import xml.etree.ElementTree as ET

ARXIV_API = "https://export.arxiv.org/api/query"


@dataclass
class ArxivEntry:
    arxiv_id: str
    title: str
    summary: str
    url: str
    published: Optional[datetime]
    updated: Optional[datetime]
    authors: list[str]


def _text(elem: Optional[ET.Element]) -> str:
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()


def _parse_dt(s: str) -> Optional[datetime]:
    if not s:
        return None
    # arXiv Atom uses ISO 8601 like "2026-01-12T18:23:45Z"
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _quote_term(term: str) -> str:
    term = term.strip()
    term = term.replace('"', '\\"')
    return f'"{term}"'


def build_arxiv_search_query(
    user_query: str,
    *,
    categories: Optional[Iterable[str]] = None,
    extra_any: Optional[Iterable[str]] = None,
) -> str:
    """
    Build a robust arXiv API 'search_query' string.

    Strategy:
    - If user_query already looks like advanced arXiv syntax (contains ':' or AND/OR/NOT),
      pass it through (lightly trimmed).
    - Otherwise:
        (all:"<full phrase>" OR (all:"t1" AND all:"t2" ...))
      and optionally:
        AND (cat:cs.AR OR cat:eess.SY ...)
      and optionally:
        AND (all:"extra1" OR all:"extra2" ...)
    """
    q = user_query.strip()
    if not q:
        raise ValueError("user_query is empty")

    # If user already provides advanced query, do not rewrite aggressively.
    if (":" in q) or re.search(r"\b(AND|OR|NOT)\b", q, flags=re.IGNORECASE):
        core = q
    else:
        tokens = [t for t in re.split(r"\s+", q) if t]
        phrase_part = f'all:{_quote_term(q)}' if len(tokens) >= 2 else ""
        and_part = " AND ".join(f'all:{_quote_term(t)}' for t in tokens) if tokens else ""

        parts = [p for p in [phrase_part, and_part] if p]
        # OR the phrase with the AND-of-tokens to avoid being too strict.
        core = " OR ".join(f"({p})" for p in parts)

    clauses = [f"({core})"]

    if categories:
        cats = [c.strip() for c in categories if c and c.strip()]
        if cats:
            cat_expr = " OR ".join(f"cat:{c}" for c in cats)
            clauses.append(f"({cat_expr})")

    if extra_any:
        extras = [e.strip() for e in extra_any if e and e.strip()]
        if extras:
            extra_expr = " OR ".join(f'all:{_quote_term(e)}' for e in extras)
            clauses.append(f"({extra_expr})")

    return " AND ".join(clauses)


def fetch_arxiv(
    query: str,
    max_results: int = 50,
    *,
    categories: Optional[list[str]] = None,
    start_dt: Optional[datetime] = None,
    end_dt: Optional[datetime] = None,
    sort_by: str = "submittedDate",  # "relevance" may exist; keep submittedDate for stable behavior
    sort_order: str = "descending",
    debug: bool = False,
) -> list[ArxivEntry]:
    """
    Fetch arXiv entries via Atom API.

    Note: arXiv API does not support true date-range filtering in the query reliably for all needs,
    so we post-filter by published time if start_dt/end_dt are provided.
    """
    if start_dt and start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    if end_dt and end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)

    search_query = build_arxiv_search_query(
        query,
        categories=categories,
        # Optional: add domain hints to improve precision for RTL/EDA topics
        extra_any=["RTL", "Verilog", "SystemVerilog", "EDA", "hardware", "chip"] if categories else None,
    )

    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": sort_order,
    }

    # ---- Self-check (prove what we actually sent) ----
    url = f"{ARXIV_API}?{urlencode(params)}"
    if debug:
        print(f"[arxiv] request_url={url}")

    resp = requests.get(ARXIV_API, params=params, timeout=30)
    if debug:
        print(f"[arxiv] status={resp.status_code} bytes={len(resp.text)}")
        # Print a small prefix so you can confirm it's Atom feed, not an error page
        print(f"[arxiv] body_prefix={resp.text[:120].replace(chr(10), ' ')}")

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

    # ---- Post-filter by time window (if requested) ----
    if start_dt or end_dt:
        filtered: list[ArxivEntry] = []
        for e in entries:
            dt = e.published or e.updated
            if dt is None:
                continue
            if start_dt and dt < start_dt:
                continue
            if end_dt and dt > end_dt:
                continue
            filtered.append(e)
        entries = filtered

    if debug:
        top = entries[:5]
        print("[arxiv] top_titles:")
        for i, e in enumerate(top, 1):
            print(f"  {i}. {e.title} | {e.url}")

    return entries
