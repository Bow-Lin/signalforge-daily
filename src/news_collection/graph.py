from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from .arxiv import ArxivEntry, fetch_arxiv
from .iflow import load_iflow_config
from .pdf_tools import fetch_and_read_pdf
from .storage import store_papers


ContentType = Literal["paper", "news", "blog", "all"]


class GraphState(TypedDict, total=False):
    topic: str
    requirements: str
    content_type: ContentType
    start: datetime | None
    end: datetime | None
    timezone: str
    max_results: int
    pdf_max_chars: int
    iflow_key: str | None
    iflow_base_url: str | None
    iflow_model: str | None
    search_query: str
    must_mention: list[str]
    plan: list[dict]
    tool_results: dict[str, object]
    candidates: dict[str, list[dict]]
    pdf_evidence: dict[str, dict]
    selected: dict[str, list[str]]
    valuable_papers: list[ArxivEntry]
    stored_papers: list[ArxivEntry]


@dataclass(frozen=True)
class GraphResult:
    stored_papers: int


logger = logging.getLogger(__name__)


@tool
def search_arxiv_tool(
    query: str,
    start_iso: str | None = None,
    end_iso: str | None = None,
    max_results: int = 50,
) -> list[dict]:
    """Search arXiv papers by topic and optional time range."""
    if start_iso in ("None", ""):
        start_iso = None
    if end_iso in ("None", ""):
        end_iso = None
    start_dt = datetime.fromisoformat(start_iso) if start_iso else None
    end_dt = datetime.fromisoformat(end_iso) if end_iso else None
    entries = fetch_arxiv(
        query,
        max_results=max_results,
        start_dt=start_dt,
        end_dt=end_dt,
    )
    payload = []
    for entry in entries:
        payload.append(
            {
                "id": entry.arxiv_id,
                "title": entry.title,
                "summary": entry.summary,
                "url": entry.url,
                "pdf_url": _arxiv_pdf_url(entry.arxiv_id),
                "published": entry.published.isoformat() if entry.published else None,
                "updated": entry.updated.isoformat() if entry.updated else None,
                "authors": entry.authors,
            }
        )
    return payload


@tool
def search_blog_tool(
    query: str,
    start_iso: str | None = None,
    end_iso: str | None = None,
    max_results: int = 50,
) -> list[dict]:
    """Search blog posts (stub)."""
    _ = (query, start_iso, end_iso, max_results)
    return []


@tool
def search_news_tool(
    query: str,
    start_iso: str | None = None,
    end_iso: str | None = None,
    max_results: int = 50,
) -> list[dict]:
    """Search news articles (stub)."""
    _ = (query, start_iso, end_iso, max_results)
    return []


@tool
def read_pdf_tool(
    url: str,
    max_chars: int = 60000,
) -> str:
    """Download and read a PDF, returning extracted text."""
    cache_dir = _paper_dir() / "pdf_cache"
    if not url.endswith(".pdf"):
        url = url + ".pdf"
    try:
        result = fetch_and_read_pdf(url=url, cache_dir=cache_dir, max_chars=max_chars)
    except Exception as exc:
        logger.warning("read_pdf_tool failed url=%s err=%s", url, exc)
        return ""
    return result.text


def _build_llm(state: GraphState, temperature: float, max_tokens: int) -> ChatOpenAI:
    config = load_iflow_config(
        api_key=state.get("iflow_key"),
        base_url=state.get("iflow_base_url"),
        model=state.get("iflow_model"),
    )
    return ChatOpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _plan_tools(state: GraphState) -> GraphState:
    llm = _build_llm(state, temperature=0.1, max_tokens=1200)
    requirements = state.get("requirements") or state.get("topic", "")
    start_iso = state.get("start").isoformat() if state.get("start") else None
    end_iso = state.get("end").isoformat() if state.get("end") else None
    content_type = state.get("content_type", "paper")
    max_results = state.get("max_results", 50)

    system = SystemMessage(
        content=(
            "You must output strict JSON only. "
            "Plan tool calls to collect candidates for the request."
        )
    )
    user = HumanMessage(
        content=(
            "Return JSON: {\"search_query\": \"...\", "
            "\"must_mention\": [\"...\"], "
            "\"plan\": [{\"tool\": \"...\", \"args\": {...}}]}\n"
            "Rules:\n"
            "- tool must be one of: search_arxiv_tool, search_blog_tool, search_news_tool\n"
            "- include start_iso/end_iso if provided, else null\n"
            "- if content_type=paper, plan only arxiv\n"
            "- if content_type=all, plan multiple tools\n\n"
            f"requirements: {requirements}\n"
            f"content_type: {content_type}\n"
            f"start_iso: {start_iso}\n"
            f"end_iso: {end_iso}\n"
            f"max_results: {max_results}\n"
        )
    )
    response = llm.invoke([system, user])
    content = response.content or "{}"

    default_tool = "search_arxiv_tool"
    if content_type == "news":
        default_tool = "search_news_tool"
    elif content_type == "blog":
        default_tool = "search_blog_tool"

    default_plan = [
        {
            "tool": default_tool,
            "args": {
                "query": requirements,
                "start_iso": start_iso,
                "end_iso": end_iso,
                "max_results": max_results,
            },
        }
    ]

    try:
        payload = json.loads(content)
        search_query = str(payload.get("search_query", "")).strip() or requirements
        must_mention = payload.get("must_mention", [])
        if not isinstance(must_mention, list):
            must_mention = []
        plan = payload.get("plan", [])
        if not isinstance(plan, list) or not plan:
            plan = default_plan
    except Exception:
        search_query = requirements
        must_mention = []
        plan = default_plan

    allowed_tools = {"search_arxiv_tool", "search_blog_tool", "search_news_tool"}
    normalized_plan: list[dict] = []
    for step in plan:
        if not isinstance(step, dict):
            continue
        tool_name = step.get("tool")
        args = step.get("args") if isinstance(step.get("args"), dict) else {}
        if tool_name not in allowed_tools:
            continue
        if "query" not in args or not args.get("query"):
            args["query"] = search_query
        if "max_results" not in args:
            args["max_results"] = max_results
        if "start_iso" not in args:
            args["start_iso"] = start_iso
        if "end_iso" not in args:
            args["end_iso"] = end_iso
        normalized_plan.append({"tool": tool_name, "args": args})

    if content_type == "paper":
        normalized_plan = [s for s in normalized_plan if s["tool"] == "search_arxiv_tool"]
    elif content_type == "news":
        normalized_plan = [s for s in normalized_plan if s["tool"] == "search_news_tool"]
    elif content_type == "blog":
        normalized_plan = [s for s in normalized_plan if s["tool"] == "search_blog_tool"]

    if not normalized_plan:
        normalized_plan = default_plan

    logger.info("plan_tools must_mention=%s plan_steps=%s", must_mention, len(normalized_plan))
    return {
        "search_query": search_query,
        "must_mention": must_mention,
        "plan": normalized_plan,
    }


def _execute_tools(state: GraphState) -> GraphState:
    plan = state.get("plan", [])
    results: dict[str, object] = {}
    candidates = {"paper": [], "blog": [], "news": []}
    tool_map = {
        "search_arxiv_tool": search_arxiv_tool,
        "search_blog_tool": search_blog_tool,
        "search_news_tool": search_news_tool,
    }

    for idx, step in enumerate(plan):
        tool_name = step.get("tool")
        args = step.get("args", {})
        tool = tool_map.get(tool_name)
        if tool is None:
            continue
        try:
            output = tool.invoke(args)
        except Exception as exc:
            logger.warning("execute_tools failed tool=%s err=%s", tool_name, exc)
            output = []
        results[f"step_{idx}"] = output
        if tool_name == "search_arxiv_tool":
            candidates["paper"].extend(output)
        elif tool_name == "search_blog_tool":
            candidates["blog"].extend(output)
        elif tool_name == "search_news_tool":
            candidates["news"].extend(output)
        logger.info("execute_tools tool=%s count=%s", tool_name, len(output))

    return {"tool_results": results, "candidates": candidates}


def _extract_snippet(text: str, must_mention: list[str], max_chars: int) -> str:
    if not text:
        return ""
    if not must_mention:
        return text[:max_chars]

    lowered = text.lower()
    snippets: list[str] = []
    remaining = max_chars
    window = 400
    for kw in must_mention:
        kw_lower = kw.lower()
        idx = lowered.find(kw_lower)
        if idx == -1:
            continue
        start = max(0, idx - window)
        end = min(len(text), idx + window)
        chunk = text[start:end]
        if len(chunk) > remaining:
            chunk = chunk[:remaining]
        snippets.append(chunk)
        remaining -= len(chunk)
        if remaining <= 0:
            break
    return "\n...\n".join(snippets)


def _read_pdfs_for_papers(state: GraphState) -> GraphState:
    candidates = state.get("candidates", {})
    papers = candidates.get("paper", [])
    must_mention = state.get("must_mention", [])
    pdf_max_chars = state.get("pdf_max_chars", 8000)
    fetch_budget = max(pdf_max_chars * 5, pdf_max_chars)
    fetch_budget = min(fetch_budget, 60000)
    pdf_evidence: dict[str, dict] = {}

    for item in papers:
        arxiv_id = item.get("id")
        if not arxiv_id:
            continue
        pdf_url = item.get("pdf_url") or _arxiv_pdf_url(arxiv_id)
        text = read_pdf_tool.invoke({"url": pdf_url, "max_chars": fetch_budget})
        mentions = {kw: (kw.lower() in (text or "").lower()) for kw in must_mention}
        snippet = _extract_snippet(text, must_mention, pdf_max_chars)
        summary = item.get("summary", "") or ""
        text_snippet = (
            f"ID: {arxiv_id}\n"
            f"TITLE: {item.get('title', '')}\n"
            f"SUMMARY: {summary}\n"
            f"MUST_MENTION_MATCH: {json.dumps(mentions)}\n"
            "PDF_EVIDENCE:\n"
            f"{snippet}"
        )
        pdf_evidence[arxiv_id] = {
            "pdf_url": pdf_url,
            "summary": summary,
            "snippet": snippet,
            "text_snippet": text_snippet,
            "mentions": mentions,
            "error": None if text else "empty_text",
        }
        logger.info(
            "read_pdfs arxiv_id=%s snippet_len=%s mentions=%s",
            arxiv_id,
            len(snippet),
            mentions,
        )

    return {"pdf_evidence": pdf_evidence}


def _final_select(state: GraphState) -> GraphState:
    llm = _build_llm(state, temperature=0.1, max_tokens=1200)
    requirements = state.get("requirements") or state.get("topic", "")
    must_mention = state.get("must_mention", [])
    candidates = state.get("candidates", {})
    pdf_evidence = state.get("pdf_evidence", {})

    paper_blocks: list[str] = []
    max_total_chars = 120000
    per_item_chars = 3000
    used = 0
    for item in candidates.get("paper", []):
        arxiv_id = item.get("id")
        evidence = pdf_evidence.get(arxiv_id, {})
        snippet = evidence.get("text_snippet", "")
        if len(snippet) > per_item_chars:
            snippet = snippet[:per_item_chars]
        if used + len(snippet) > max_total_chars:
            break
        paper_blocks.append(snippet)
        used += len(snippet)

    def _format_items(items: list[dict]) -> str:
        lines = []
        for item in items:
            lines.append(
                f"ID: {item.get('id')}\n"
                f"TITLE: {item.get('title', '')}\n"
                f"SUMMARY: {item.get('summary', '')}\n"
                f"URL: {item.get('url', '')}\n"
                f"PUBLISHED: {item.get('published', '')}\n"
            )
        return "\n".join(lines)

    system = SystemMessage(
        content=(
            "You must output strict JSON only. "
            "Select items that satisfy the requirements."
        )
    )
    papers_text = "\n\n".join(paper_blocks)
    user = HumanMessage(
        content=(
            f"requirements: {requirements}\n"
            f"must_mention: {must_mention}\n\n"
            "PAPERS:\n"
            f"{papers_text}\n\n"
            "BLOGS:\n"
            f"{_format_items(candidates.get('blog', []))}\n\n"
            "NEWS:\n"
            f"{_format_items(candidates.get('news', []))}\n\n"
            "Return JSON: {\"paper\": [ids], \"blog\": [ids], \"news\": [ids]}"
        )
    )
    response = llm.invoke([system, user])
    content = response.content or "{}"

    selected = {"paper": [], "blog": [], "news": []}
    try:
        payload = json.loads(content)
        for key in ("paper", "blog", "news"):
            ids = payload.get(key, [])
            if isinstance(ids, list):
                selected[key] = [str(i) for i in ids]
    except Exception:
        selected = {"paper": [], "blog": [], "news": []}

    valid_ids = {
        "paper": {item.get("id") for item in candidates.get("paper", [])},
        "blog": {item.get("id") for item in candidates.get("blog", [])},
        "news": {item.get("id") for item in candidates.get("news", [])},
    }
    for key in ("paper", "blog", "news"):
        selected[key] = [item for item in selected[key] if item in valid_ids[key]]

    logger.info(
        "final_select selected paper=%s blog=%s news=%s",
        len(selected["paper"]),
        len(selected["blog"]),
        len(selected["news"]),
    )
    return {"selected": selected}


def _build_valuable_items(state: GraphState) -> GraphState:
    selected = state.get("selected", {})
    paper_ids = set(selected.get("paper", []))
    papers: list[ArxivEntry] = []

    for item in state.get("candidates", {}).get("paper", []):
        if item.get("id") not in paper_ids:
            continue
        papers.append(
            ArxivEntry(
                arxiv_id=item.get("id", ""),
                title=item.get("title", ""),
                summary=item.get("summary", ""),
                url=item.get("url", ""),
                published=datetime.fromisoformat(item["published"])
                if item.get("published")
                else None,
                updated=datetime.fromisoformat(item["updated"])
                if item.get("updated")
                else None,
                authors=item.get("authors", []) or [],
            )
        )

    return {"valuable_papers": papers}


def _store_items(state: GraphState) -> GraphState:
    papers = state.get("valuable_papers", [])
    if not papers:
        logger.info("store_papers no valuable papers to save")
        return {"stored_papers": []}
    stored = store_papers(papers, _paper_dir())
    logger.info("store_papers stored=%s", len(stored))
    return {"stored_papers": stored}


def build_graph() -> StateGraph:
    graph = StateGraph(GraphState)
    graph.add_node("plan_tools", _plan_tools)
    graph.add_node("execute_tools", _execute_tools)
    graph.add_node("read_pdfs_for_papers", _read_pdfs_for_papers)
    graph.add_node("final_select", _final_select)
    graph.add_node("build_valuable_items", _build_valuable_items)
    graph.add_node("store", _store_items)
    graph.set_entry_point("plan_tools")
    graph.add_edge("plan_tools", "execute_tools")
    graph.add_edge("execute_tools", "read_pdfs_for_papers")
    graph.add_edge("read_pdfs_for_papers", "final_select")
    graph.add_edge("final_select", "build_valuable_items")
    graph.add_edge("build_valuable_items", "store")
    graph.add_edge("store", END)
    return graph


def run_collection(
    topic: str,
    content_type: ContentType,
    start: datetime | None,
    end: datetime | None,
    tz: str,
    iflow_key: str | None,
    iflow_base_url: str | None,
    iflow_model: str | None,
    max_results: int,
    pdf_max_chars: int,
) -> GraphResult:
    if content_type not in ("paper", "all", "news", "blog"):
        return GraphResult(stored_papers=0)
    graph = build_graph().compile()
    result = graph.invoke(
        {
            "topic": topic,
            "requirements": topic,
            "content_type": content_type,
            "start": start,
            "end": end,
            "timezone": tz,
            "iflow_key": iflow_key,
            "iflow_base_url": iflow_base_url,
            "iflow_model": iflow_model,
            "max_results": max_results,
            "pdf_max_chars": pdf_max_chars,
            "search_query": "",
            "must_mention": [],
            "plan": [],
            "tool_results": {},
            "candidates": {"paper": [], "blog": [], "news": []},
            "pdf_evidence": {},
            "selected": {"paper": [], "blog": [], "news": []},
            "valuable_papers": [],
            "stored_papers": [],
        }
    )
    return GraphResult(stored_papers=len(result.get("stored_papers", [])))


def _paper_dir() -> Path:
    return Path("/home/deming/work/collection/paper")


def _arxiv_pdf_url(arxiv_id: str) -> str:
    if "/abs/" in arxiv_id:
        return arxiv_id.replace("/abs/", "/pdf/") + ".pdf"
    if arxiv_id.endswith(".pdf"):
        return arxiv_id
    return arxiv_id + ".pdf"
