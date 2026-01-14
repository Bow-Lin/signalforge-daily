from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Annotated, Literal, TypedDict, cast

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from .arxiv import ArxivEntry, arxiv_pdf_url, fetch_arxiv, filter_by_date
from .iflow import load_iflow_config
from .pdf_tools import fetch_and_read_pdf
from .storage import store_papers


ContentType = Literal["paper", "news", "blog", "all"]


class GraphState(TypedDict, total=False):
    topic: str
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
    valuable_papers: list[ArxivEntry]
    stored_papers: list[ArxivEntry]


@dataclass(frozen=True)
class GraphResult:
    stored_papers: int


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
    entries = fetch_arxiv(query, max_results=max_results)
    start = datetime.fromisoformat(start_iso) if start_iso else None
    end = datetime.fromisoformat(end_iso) if end_iso else None
    filtered = filter_by_date(entries, start, end)
    payload = []
    for entry in filtered:
        payload.append(
            {
                "id": entry.arxiv_id,
                "title": entry.title,
                "summary": entry.summary,
                "url": entry.url,
                "pdf_url": arxiv_pdf_url(entry.arxiv_id),
                "published": entry.published.isoformat(),
                "updated": entry.updated.isoformat(),
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
    result = fetch_and_read_pdf(url=url, cache_dir=cache_dir, max_chars=max_chars)
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
    return llm.bind_tools([search_arxiv_tool, read_pdf_tool])


def _agent_node(state: GraphState) -> GraphState:
    llm = _build_agent(state)
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


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
                papers[arxiv_id] = ArxivEntry(
                    arxiv_id=arxiv_id,
                    title=cast(str, item["title"]),
                    summary=cast(str, item["summary"]),
                    url=cast(str, item["url"]),
                    published=datetime.fromisoformat(cast(str, item["published"])),
                    updated=datetime.fromisoformat(cast(str, item["updated"])),
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
        break

    valuable = [papers[pid] for pid in final_ids if pid in papers]
    return {"papers": papers, "valuable_papers": valuable}


def _store_papers(state: GraphState) -> GraphState:
    papers = state.get("valuable_papers") or []
    if not papers:
        return {"stored_papers": []}
    stored = store_papers(papers, _paper_dir())
    return {"stored_papers": stored}


def _paper_dir() -> "Path":
    return Path("/home/deming/work/collection/paper")


def build_graph() -> StateGraph:
    graph = StateGraph(GraphState)
    graph.add_node("agent", _agent_node)
    graph.add_node("tools", ToolNode([search_arxiv_tool, read_pdf_tool]))
    graph.add_node("collect_results", _collect_results)
    graph.add_node("store_papers", _store_papers)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "collect_results"})
    graph.add_edge("tools", "agent")
    graph.add_edge("collect_results", "store_papers")
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
    graph = build_graph().compile()
    start_iso = start.isoformat() if start else None
    end_iso = end.isoformat() if end else None
    system = SystemMessage(
        content=(
            "You are a research assistant that uses tools to find and evaluate papers.\n"
            "Process:\n"
            "1) Use search_arxiv_tool to find papers for the topic and time range.\n"
            "2) For each candidate, call read_pdf_tool on its pdf_url and pass max_chars.\n"
            "3) Decide which papers are valuable for the topic.\n"
            "Output: a JSON array of paper IDs to keep, no extra text."
        )
    )
    user = HumanMessage(
        content=(
            f"Topic: {topic}\n"
            f"Start ISO: {start_iso}\n"
            f"End ISO: {end_iso}\n"
            f"Max results: {max_results}\n"
            f"PDF max chars: {pdf_max_chars}"
        )
    )
    result = graph.invoke(
        {
            "topic": topic,
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
            "papers": {},
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
