from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Annotated, Literal, TypedDict, cast

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .arxiv import ArxivEntry, fetch_arxiv
from .iflow import load_iflow_config
from .pdf_tools import fetch_and_read_pdf
from .storage import store_papers


ContentType = Literal["paper", "news", "blog", "all"]


class GraphState(TypedDict, total=False):
    topic: str
    requirements: str
    search_query: str
    must_mention: list[str]
    content_type: ContentType
    start: datetime | None
    end: datetime | None
    timezone: str
    iflow_key: str | None
    iflow_base_url: str | None
    iflow_model: str | None
    max_results: int
    pdf_max_chars: int
    messages: Annotated[list[BaseMessage], add_messages]
    papers: dict[str, ArxivEntry]
    pdf_texts: dict[str, str]
    valuable_papers: list[ArxivEntry]
    stored_papers: list[ArxivEntry]


@dataclass(frozen=True)
class GraphResult:
    stored_papers: int


logger = logging.getLogger(__name__)


_MAX_LLM_INPUT_CHARS = 200000


def _truncate_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    total = sum(len(getattr(m, "content", "") or "") for m in messages)
    if total <= _MAX_LLM_INPUT_CHARS:
        return messages

    truncated: list[BaseMessage] = []
    remaining = _MAX_LLM_INPUT_CHARS
    for msg in messages:
        content = getattr(msg, "content", "") or ""
        if not content:
            truncated.append(msg)
            continue
        if remaining <= 0:
            truncated.append(HumanMessage(content="(truncated due to input limit)"))
            break
        if content.startswith("pdf_text for "):
            if len(content) > remaining:
                content = content[:remaining]
            remaining -= len(content)
            truncated.append(HumanMessage(content=content))
        else:
            if len(content) > remaining:
                content = content[:remaining]
            remaining -= len(content)
            truncated.append(HumanMessage(content=content))
    return truncated


def _extract_intent(state: GraphState) -> GraphState:
    config = load_iflow_config(
        api_key=state.get("iflow_key"),
        base_url=state.get("iflow_base_url"),
        model=state.get("iflow_model"),
    )
    llm = ChatOpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model,
        temperature=0.1,
        max_tokens=8000,
    )
    requirements = state.get("requirements") or state.get("topic", "")
    prompt = (
        "You extract a search query and must-mention keywords from a user request.\n"
        "Return JSON: {\"search_query\": \"...\", \"must_mention\": [\"...\"]}.\n"
        "Rules:\n"
        "- search_query should be short and suitable for arXiv search.\n"
        "- must_mention are exact dataset or keyword constraints to check in PDFs.\n"
        "- If none, return an empty list.\n\n"
        f"Request: {requirements}\n"
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content or "{}"
    try:
        payload = json.loads(content)
        search_query = str(payload.get("search_query", "")).strip()
        must_mention = payload.get("must_mention", [])
        if not isinstance(must_mention, list):
            must_mention = []
    except Exception:
        search_query = requirements
        must_mention = []

    if not search_query:
        search_query = requirements

    logger.info("intent search_query=%s must_mention=%s", search_query, must_mention)
    return {"search_query": search_query, "must_mention": must_mention}


def _inject_intent_message(state: GraphState) -> GraphState:
    search_query = state.get("search_query", "")
    must_mention = state.get("must_mention", [])
    msg = HumanMessage(
        content=(
            f"search_query: {search_query}\n"
            f"must_mention: {json.dumps(must_mention)}"
        )
    )
    return {"messages": [msg]}


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
    logger.info(
        "search_arxiv_tool query=%s start=%s end=%s max_results=%s",
        query,
        start_iso,
        end_iso,
        max_results,
    )
    entries = fetch_arxiv(
        query,
        max_results=max_results,
        start_dt=start_dt,
        end_dt=end_dt,
    )
    logger.info("search_arxiv_tool fetched=%s", len(entries))
    logger.info("search_arxiv_tool titles=%s", [entry.title for entry in entries])
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
def read_pdf_tool(
    url: str,
    max_chars: int = 8000,
) -> str:
    """Download and read a PDF, returning extracted text."""
    cache_dir = _paper_dir() / "pdf_cache"
    if not url.endswith(".pdf"):
        url = url + ".pdf"
    logger.info("read_pdf_tool url=%s max_chars=%s", url, max_chars)
    try:
        result = fetch_and_read_pdf(url=url, cache_dir=cache_dir, max_chars=max_chars)
    except Exception as exc:
        logger.warning("read_pdf_tool failed url=%s err=%s", url, exc)
        return ""
    logger.info("read_pdf_tool text_chars=%s", len(result.text))
    return result.text


def _build_agent(state: GraphState) -> ChatOpenAI:
    config = load_iflow_config(
        api_key=state.get("iflow_key"),
        base_url=state.get("iflow_base_url"),
        model=state.get("iflow_model"),
    )
    llm = ChatOpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    return llm.bind_tools([search_arxiv_tool])


def _agent_node(state: GraphState) -> GraphState:
    llm = _build_agent(state)
    messages = _truncate_messages(state["messages"])
    logger.info("agent step messages=%s", len(messages))
    response = llm.invoke(messages)
    logger.debug("agent response tool_calls=%s", getattr(response, "tool_calls", None))
    logger.debug("agent response content_len=%s", len(response.content or ""))
    return {"messages": [response]}


def _needs_tool_followup(state: GraphState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return "collect_results"
    last = messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"

    has_search = False
    has_read_pdf = False
    for msg in messages:
        tool_name = getattr(msg, "name", "")
        if tool_name == "search_arxiv_tool":
            has_search = True
        if tool_name == "read_pdf_tool":
            has_read_pdf = True

    if has_search and not has_read_pdf:
        return "force_read"
    return "collect_results"


def _force_read_prompt(state: GraphState) -> GraphState:
    note = HumanMessage(
        content=(
            "PDFs will be read automatically for each candidate paper "
            "returned by search_arxiv_tool. Do not construct URLs yourself."
        )
    )
    return {"messages": [note]}


def _auto_read_pdfs(state: GraphState) -> GraphState:
    papers = state.get("papers") or {}
    if not papers:
        return {"pdf_texts": {}}
    pdf_texts: dict[str, str] = {}
    for arxiv_id, entry in papers.items():
        try:
            text = read_pdf_tool.invoke(
                {"url": _arxiv_pdf_url(entry.arxiv_id), "max_chars": state.get("pdf_max_chars", 8000)}
            )
            pdf_texts[arxiv_id] = text or ""
        except Exception as exc:
            logger.warning("read_pdf_tool failed url=%s err=%s", entry.arxiv_id, exc)
            pdf_texts[arxiv_id] = ""
    return {"pdf_texts": pdf_texts}


def _must_mentions_present(text: str, must_mention: list[str]) -> bool:
    if not must_mention:
        return True
    lowered = text.lower()
    return all(m.lower() in lowered for m in must_mention)


def _evaluate_each(state: GraphState) -> GraphState:
    papers = state.get("papers") or {}
    if not papers:
        return {"valuable_papers": []}
    pdf_texts = state.get("pdf_texts") or {}
    must_mention = state.get("must_mention") or []
    config = load_iflow_config(
        api_key=state.get("iflow_key"),
        base_url=state.get("iflow_base_url"),
        model=state.get("iflow_model"),
    )
    llm = ChatOpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model,
        temperature=0.1,
        max_tokens=800,
    )
    valuable: list[ArxivEntry] = []
    for arxiv_id, entry in papers.items():
        text = pdf_texts.get(arxiv_id, "")
        if must_mention and not _must_mentions_present(text, must_mention):
            continue
        prompt = (
            "Determine if the paper is valuable for the requirements.\n"
            "Return JSON: {\"valuable\": true/false} with no extra text.\n"
            "Requirements must be satisfied, including any dataset mentions.\n\n"
            f"Requirements: {state.get('requirements') or state.get('topic')}\n"
            f"Title: {entry.title}\n"
            f"Summary: {entry.summary}\n"
            "PDF (excerpt or full):\n"
            f"{text}\n"
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        try:
            payload = json.loads(response.content or "{}")
            if bool(payload.get("valuable", False)):
                valuable.append(entry)
        except Exception:
            continue
    return {"valuable_papers": valuable}


def _collect_results(state: GraphState) -> GraphState:
    papers: dict[str, ArxivEntry] = {}
    for msg in state["messages"]:
        tool_name = getattr(msg, "name", "")
        if tool_name != "search_arxiv_tool":
            continue
        try:
            payload = json.loads(msg.content)
        except Exception:
            continue
        if not isinstance(payload, list):
            continue
        for item in payload:
            try:
                arxiv_id = cast(str, item["id"])
                published_raw = item.get("published")
                updated_raw = item.get("updated")
                papers[arxiv_id] = ArxivEntry(
                    arxiv_id=arxiv_id,
                    title=cast(str, item["title"]),
                    summary=cast(str, item["summary"]),
                    url=cast(str, item["url"]),
                    published=datetime.fromisoformat(published_raw)
                    if published_raw
                    else None,
                    updated=datetime.fromisoformat(updated_raw) if updated_raw else None,
                    authors=cast(list[str], item["authors"]),
                )
            except Exception:
                continue

    final_ids: list[str] = []
    for msg in reversed(state["messages"]):
        if msg.type != "ai":
            continue
        try:
            final_ids = json.loads(msg.content)
        except Exception:
            final_ids = []
        logger.debug("collect_results final_ai_content_len=%s", len(msg.content or ""))
        break

    valuable = [papers[pid] for pid in final_ids if pid in papers]
    logger.info(
        "collect_results papers=%s valuable=%s", len(papers), len(valuable)
    )
    return {"papers": papers, "valuable_papers": valuable}


def _store_papers(state: GraphState) -> GraphState:
    papers = state.get("valuable_papers") or []
    if not papers:
        logger.info("store_papers no valuable papers to save")
        return {"stored_papers": []}
    stored = store_papers(papers, _paper_dir())
    logger.info("store_papers stored=%s", len(stored))
    return {"stored_papers": stored}


def _paper_dir() -> "Path":
    return Path("/home/deming/work/collection/paper")


def _arxiv_pdf_url(arxiv_id: str) -> str:
    if "/abs/" in arxiv_id:
        return arxiv_id.replace("/abs/", "/pdf/") + ".pdf"
    if arxiv_id.endswith(".pdf"):
        return arxiv_id
    return arxiv_id + ".pdf"


def build_graph() -> StateGraph:
    graph = StateGraph(GraphState)
    graph.add_node("intent", _extract_intent)
    graph.add_node("inject_intent", _inject_intent_message)
    graph.add_node("agent", _agent_node)
    graph.add_node("tools", ToolNode([search_arxiv_tool]))
    graph.add_node("force_read", _force_read_prompt)
    graph.add_node("auto_read_pdfs", _auto_read_pdfs)
    graph.add_node("collect_results", _collect_results)
    graph.add_node("evaluate_each", _evaluate_each)
    graph.add_node("store_papers", _store_papers)
    graph.set_entry_point("intent")
    graph.add_edge("intent", "inject_intent")
    graph.add_edge("inject_intent", "agent")
    graph.add_conditional_edges(
        "agent",
        _needs_tool_followup,
        {"tools": "tools", "force_read": "force_read", "collect_results": "collect_results"},
    )
    graph.add_edge("tools", "agent")
    graph.add_edge("force_read", "collect_results")
    graph.add_edge("collect_results", "auto_read_pdfs")
    graph.add_edge("auto_read_pdfs", "evaluate_each")
    graph.add_edge("evaluate_each", "store_papers")
    graph.add_edge("store_papers", END)
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
    if content_type not in ("paper", "all"):
        return GraphResult(stored_papers=0)
    logger.info(
        "run_collection topic=%s start=%s end=%s max_results=%s pdf_max_chars=%s",
        topic,
        start,
        end,
        max_results,
        pdf_max_chars,
    )
    graph = build_graph().compile()
    start_iso = start.isoformat() if start else None
    end_iso = end.isoformat() if end else None
    requirements = topic
    system = SystemMessage(
        content=(
            "You are a research assistant that uses tools to find and evaluate papers.\n"
            "Process:\n"
            "1) Use search_arxiv_tool with the provided search_query and time range.\n"
            "2) PDFs will be read automatically for each candidate.\n"
            "3) Keep papers only if they match the core topic AND mention all must_mention keywords.\n"
            "Output: a JSON array of paper IDs to keep, no extra text.\n"
            "If none match, output [] exactly."
        )
    )
    user = HumanMessage(
        content=(
            f"Requirements: {requirements}\n"
            f"Start ISO: {start_iso}\n"
            f"End ISO: {end_iso}\n"
            f"Max results: {max_results}\n"
            f"PDF max chars: {pdf_max_chars}\n"
            "Use search_query and must_mention provided by intent extraction."
        )
    )
    result = graph.invoke(
        {
            "topic": topic,
            "requirements": requirements,
            "content_type": content_type,
            "start": start,
            "end": end,
            "timezone": tz,
            "iflow_key": iflow_key,
            "iflow_base_url": iflow_base_url,
            "iflow_model": iflow_model,
            "max_results": max_results,
            "pdf_max_chars": pdf_max_chars,
            "messages": [system, user],
            "search_query": "",
            "must_mention": [],
            "papers": {},
            "pdf_texts": {},
            "valuable_papers": [],
            "stored_papers": [],
        }
    )
    return GraphResult(stored_papers=len(result.get("stored_papers", [])))


def parse_datetime(value: str, tz: str) -> datetime:
    from zoneinfo import ZoneInfo

    value = value.strip()
    if "T" not in value:
        value = value + "T00:00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz))
    return dt.astimezone(timezone.utc)
