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


_ADVANCED_RE = re.compile(r"(:)|\b(AND|OR|NOT)\b", flags=re.IGNORECASE)


def looks_advanced_arxiv_query(q: str) -> bool:
    q = (q or "").strip()
    if not q:
        return False
    return bool(_ADVANCED_RE.search(q))


def _quote_term(term: str) -> str:
    """
    Quote a term for arXiv query.
    We keep it simple: escape double-quotes and wrap in quotes.
    """
    term = (term or "").strip()
    term = term.replace('"', '\\"')
    return f'"{term}"'


def _split_tokens(q: str) -> list[str]:
    q = (q or "").strip()
    if not q:
        return []
    # Keep hyphens/underscores inside tokens; split on whitespace.
    toks = [t for t in re.split(r"\s+", q) if t]
    # Dedup while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for t in toks:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def build_arxiv_search_query(
    user_query: str,
    *,
    categories: Optional[Iterable[str]] = None,
    extra_any: Optional[Iterable[str]] = None,
    allow_all_field_fallback: bool = True,
) -> str:
    """
    Build a robust arXiv API 'search_query' string.

    Goals:
    - Prefer ti:/abs: over all: to reduce noise.
    - If user already provides advanced arXiv syntax (contains ':' or AND/OR/NOT),
      pass it through (lightly trimmed), and only append optional cat filters.
    - Otherwise generate an OR-combination to improve recall:
        (
          (ti:"full phrase" OR abs:"full phrase")
          OR ((ti:"t1" AND ti:"t2" ...) OR (abs:"t1" AND abs:"t2" ...))
          OR (all:"full phrase")              # optional fallback
        )
      And optionally:
        AND (cat:cs.AR OR cat:eess.SY ...)
      And optionally:
        OR (all:"extra1" OR all:"extra2" ...)   # soft expansion, NOT hard filter
    """
    q = (user_query or "").strip()
    if not q:
        raise ValueError("user_query is empty")

    # If user already provides advanced query, do not rewrite it.
    if looks_advanced_arxiv_query(q):
        core = q
        clauses = [f"({core})"]
    else:
        tokens = _split_tokens(q)

        phrase_clause = ""
        if len(tokens) >= 2:
            phrase = _quote_term(q)
            phrase_clause = f"(ti:{phrase} OR abs:{phrase})"

        token_ti_and = ""
        token_abs_and = ""
        if tokens:
            token_ti_and = " AND ".join(f"ti:{_quote_term(t)}" for t in tokens)
            token_abs_and = " AND ".join(f"abs:{_quote_term(t)}" for t in tokens)

        token_clause = ""
        if token_ti_and and token_abs_and:
            token_clause = f"(({token_ti_and}) OR ({token_abs_and}))"
        elif token_ti_and:
            token_clause = f"({token_ti_and})"

        all_fallback = ""
        if allow_all_field_fallback and len(tokens) >= 2:
            all_fallback = f"(all:{_quote_term(q)})"
        elif allow_all_field_fallback and len(tokens) == 1:
            # For single token, all: is a reasonable fallback.
            all_fallback = f"(all:{_quote_term(tokens[0])})"

        parts = [p for p in [phrase_clause, token_clause, all_fallback] if p]
        core = " OR ".join(parts) if parts else f"(all:{_quote_term(q)})"

        clauses = [f"({core})"]

    # Category filter is a true AND constraint (when provided).
    if categories:
        cats = [c.strip() for c in categories if c and c.strip()]
        if cats:
            cat_expr = " OR ".join(f"cat:{c}" for c in cats)
            clauses.append(f"({cat_expr})")

    # extra_any is a SOFT expansion: we OR it into the core rather than AND-filtering.
    if extra_any:
        extras = [e.strip() for e in extra_any if e and e.strip()]
        if extras:
            extra_expr = " OR ".join(f'all:{_quote_term(e)}' for e in extras)
            # Expand recall: (existing) OR (extra terms)
            clauses[0] = f"({clauses[0]} OR ({extra_expr}))"

    return " AND ".join(clauses)


def _default_domain_hints(query: str) -> list[str]:
    """
    Domain hints used as soft expansion for recall.
    Keep these broad; final selection will do semantic filtering.
    """
    # You can tune this list per your project domain.
    return [
        "RTL",
        "Verilog",
        "SystemVerilog",
        "HDL",
        "EDA",
        "hardware",
        "chip",
        "logic synthesis",
        "spec-to-rtl",
    ]


def _pick_sort_by(
    query: str,
    *,
    start_dt: Optional[datetime],
    end_dt: Optional[datetime],
    user_sort_by: Optional[str],
) -> str:
    """
    Heuristic:
    - If user explicitly sets sort_by: respect it.
    - If a time window is provided, submittedDate is usually preferred.
    - If query is non-advanced and no time window, relevance tends to match website better.
    """
    if user_sort_by:
        return user_sort_by
    if start_dt or end_dt:
        return "submittedDate"
    if looks_advanced_arxiv_query(query):
        return "submittedDate"
    return "relevance"


def fetch_arxiv(
    query: str,
    max_results: int = 50,
    *,
    categories: Optional[list[str]] = None,
    start_dt: Optional[datetime] = None,
    end_dt: Optional[datetime] = None,
    sort_by: Optional[str] = None,  # None = auto
    sort_order: str = "descending",
    debug: bool = False,
    extra_any: Optional[list[str]] = None,
) -> list[ArxivEntry]:
    """
    Fetch arXiv entries via Atom API.

    Note: arXiv API does not support true date-range filtering in the query reliably,
    so we post-filter by (published or updated) time if start_dt/end_dt are provided.
    """
    if start_dt and start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    if end_dt and end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)

    sort_by_final = _pick_sort_by(query, start_dt=start_dt, end_dt=end_dt, user_sort_by=sort_by)

    # Soft expansion: always enabled unless explicitly overridden by extra_any=[].
    if extra_any is None:
        extra_any = _default_domain_hints(query)

    search_query = build_arxiv_search_query(
        query,
        categories=categories,
        extra_any=extra_any,
        allow_all_field_fallback=True,
    )

    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_by_final,
        "sortOrder": sort_order,
    }

    # ---- Self-check (prove what we actually sent) ----
    url = f"{ARXIV_API}?{urlencode(params)}"
    if debug:
        print(f"[arxiv] request_url={url}")

    resp = requests.get(ARXIV_API, params=params, timeout=30)
    if debug:
        print(f"[arxiv] status={resp.status_code} bytes={len(resp.text)}")
        print(f"[arxiv] body_prefix={resp.text[:160].replace(chr(10), ' ')}")

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
        top = entries[:10]
        print(f"[arxiv] sortBy={sort_by_final} returned={len(entries)}")
        print("[arxiv] top_titles:")
        for i, e in enumerate(top, 1):
            print(f"  {i}. {e.title} | {e.url}")

    return entries
