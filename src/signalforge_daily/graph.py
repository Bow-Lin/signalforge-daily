from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import shutil
from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from .arxiv import ArxivEntry, fetch_arxiv
from .iflow import load_iflow_config
from .pdf_tools import fetch_and_read_pdf
from .storage import store_papers
from .telemetry import flush, log_generation, log_span, start_trace, update_trace_name


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
    session_id: str | None
    trace_id: str | None
    search_query: str
    must_mention: list[str]
    plan: list[dict]
    tool_results: dict[str, object]
    candidates: dict[str, list[dict]]
    pdf_evidence: dict[str, dict]
    selected: dict[str, list[str]]
    quality_min_score: float
    paper_rubric: list[dict]
    paper_scores: dict[str, dict]
    paper_reasons: dict[str, list[str]]
    valuable_papers: list[ArxivEntry]
    stored_papers: list[ArxivEntry]


@dataclass(frozen=True)
class GraphResult:
    stored_papers: int


logger = logging.getLogger(__name__)

DEFAULT_QUALITY_MIN_SCORE = 7.0
DEFAULT_PAPER_RUBRIC = [
    {"name": "relevance_to_topic", "weight": 2},
    {"name": "contribution_novelty", "weight": 2},
    {"name": "method_clarity", "weight": 2},
    {"name": "experimental_evidence", "weight": 3},
    {"name": "reproducibility_signals", "weight": 1},
]
MAX_PAPER_CANDIDATES = 20


def _normalize_quality_min_score(value: object) -> float:
    if isinstance(value, bool):
        return DEFAULT_QUALITY_MIN_SCORE
    try:
        score = float(value)
    except (TypeError, ValueError):
        return DEFAULT_QUALITY_MIN_SCORE
    if score < 0:
        return 0.0
    if score > 10:
        return 10.0
    return score


def _normalize_paper_rubric(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return list(DEFAULT_PAPER_RUBRIC)
    rubric: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        weight = item.get("weight")
        try:
            weight_int = int(weight)
        except (TypeError, ValueError):
            continue
        if not name or weight_int <= 0:
            continue
        rubric.append({"name": name, "weight": weight_int})
    if not rubric:
        return list(DEFAULT_PAPER_RUBRIC)
    return rubric


def _load_json_with_repair(content: str) -> dict | None:
    try:
        return json.loads(content)
    except Exception:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(content[start : end + 1])
        except Exception:
            return None


def _make_query_variants(topic: str) -> list[str]:
    base = " ".join((topic or "").split())
    variants: list[str] = []

    def add(value: str) -> None:
        cleaned = " ".join((value or "").split())
        if cleaned and cleaned not in variants:
            variants.append(cleaned)

    add(base)
    if not base:
        return variants
    normalized = " ".join(base.replace("-", " ").replace("_", " ").split())
    add(normalized)
    if " " in normalized:
        add(normalized.replace(" ", "-"))
    if len(variants) < 2:
        add(f"{normalized} method")
    if len(variants) < 3:
        add(f"{normalized} system")
    if len(variants) < 4:
        add(f"{normalized} model")
    return variants


def _ensure_arxiv_plan(
    plan: list[dict],
    *,
    topic: str,
    start_iso: str | None,
    end_iso: str | None,
    max_results: int,
) -> list[dict]:
    existing_queries: list[str] = []
    unique_plan: list[dict] = []
    for step in plan:
        if step.get("tool") != "search_arxiv_tool":
            continue
        args = step.get("args", {})
        query = str(args.get("query", "")).strip()
        if not query or query in existing_queries:
            continue
        existing_queries.append(query)
        unique_plan.append(step)
    if len(existing_queries) >= 2:
        return unique_plan[:4]

    variants = _make_query_variants(topic)
    enriched = list(unique_plan)
    for query in variants:
        if query in existing_queries:
            continue
        enriched.append(
            {
                "tool": "search_arxiv_tool",
                "args": {
                    "query": query,
                    "start_iso": start_iso,
                    "end_iso": end_iso,
                    "max_results": max_results,
                },
            }
        )
        existing_queries.append(query)
        if len(existing_queries) >= 2:
            break
    return enriched[:4]


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
        "search_arxiv_tool query=%s start_iso=%s end_iso=%s max_results=%s",
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
        debug=True,
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
    trace_id = state.get("trace_id")
    topic = state.get("topic", "")
    requirements = state.get("requirements") or topic
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
            "\"plan\": [{\"tool\": \"...\", \"args\": {...}}], "
            "\"quality_min_score\": 7.0, "
            "\"paper_rubric\": [{\"name\": \"...\", \"weight\": 2}]}\n"
            "Rules:\n"
            "- tool must be one of: search_arxiv_tool, search_blog_tool, search_news_tool\n"
            "- include start_iso/end_iso if provided, else null\n"
            "- if content_type=paper, plan only arxiv\n"
            "- if content_type=paper, create 2-4 search_arxiv_tool steps with different "
            "query variants focused on the topic (avoid adding quality filters)\n"
            "- quality_min_score defaults to 7.0 unless requirements explicitly request otherwise\n"
            "- paper_rubric items must include name and integer weight\n"
            "- if content_type=all, plan multiple tools\n\n"
            f"topic: {topic}\n"
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
                "query": topic,
                "start_iso": start_iso,
                "end_iso": end_iso,
                "max_results": max_results,
            },
        }
    ]

    try:
        payload = json.loads(content)
        search_query = str(payload.get("search_query", "")).strip() or topic
        must_mention = payload.get("must_mention", [])
        if not isinstance(must_mention, list):
            must_mention = []
        plan = payload.get("plan", [])
        if not isinstance(plan, list) or not plan:
            plan = default_plan
        quality_min_score = _normalize_quality_min_score(
            payload.get("quality_min_score", DEFAULT_QUALITY_MIN_SCORE)
        )
        paper_rubric = _normalize_paper_rubric(payload.get("paper_rubric", []))
    except Exception:
        search_query = topic
        must_mention = []
        plan = default_plan
        quality_min_score = DEFAULT_QUALITY_MIN_SCORE
        paper_rubric = list(DEFAULT_PAPER_RUBRIC)

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
        normalized_plan = _ensure_arxiv_plan(
            normalized_plan,
            topic=search_query or topic,
            start_iso=start_iso,
            end_iso=end_iso,
            max_results=max_results,
        )
    elif content_type == "news":
        normalized_plan = [s for s in normalized_plan if s["tool"] == "search_news_tool"]
    elif content_type == "blog":
        normalized_plan = [s for s in normalized_plan if s["tool"] == "search_blog_tool"]

    if not normalized_plan:
        normalized_plan = default_plan

    logger.info(
        "plan_tools must_mention=%s plan_steps=%s quality_min_score=%s",
        must_mention,
        len(normalized_plan),
        quality_min_score,
    )
    plan_input = {
        "topic": topic,
        "requirements": requirements,
        "content_type": content_type,
        "start_iso": start_iso,
        "end_iso": end_iso,
        "max_results": max_results,
        "prompt_chars": len(system.content) + len(user.content),
    }
    logger.info("plan_tools langfuse_input=%s", plan_input)
    usage = getattr(response, "response_metadata", {}).get("token_usage")
    log_generation(
        trace_id=trace_id,
        name="plan_tools",
        model=llm.model_name,
        input=plan_input,
        output={
            "search_query": search_query,
            "must_mention": must_mention,
            "plan": normalized_plan,
            "quality_min_score": quality_min_score,
            "paper_rubric": paper_rubric,
        },
        usage=usage,
    )
    return {
        "search_query": search_query,
        "must_mention": must_mention,
        "plan": normalized_plan,
        "quality_min_score": quality_min_score,
        "paper_rubric": paper_rubric,
    }


def _execute_tools(state: GraphState) -> GraphState:
    plan = state.get("plan", [])
    results: dict[str, object] = {}
    candidates = {"paper": [], "blog": [], "news": []}
    trace_id = state.get("trace_id")
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
        logger.info("execute_tools tool=%s args=%s", tool_name, args)
        try:
            output = tool.invoke(args)
            log_span(
                trace_id=trace_id,
                name=tool_name,
                input=args,
                output={"count": len(output)},
                as_type="tool",
            )
        except Exception as exc:
            logger.warning("execute_tools failed tool=%s err=%s", tool_name, exc)
            log_span(
                trace_id=trace_id,
                name=tool_name,
                input=args,
                output={"count": 0},
                error=str(exc),
                as_type="tool",
            )
            output = []
        results[f"step_{idx}"] = output
        if tool_name == "search_arxiv_tool":
            candidates["paper"].extend(output)
        elif tool_name == "search_blog_tool":
            candidates["blog"].extend(output)
        elif tool_name == "search_news_tool":
            candidates["news"].extend(output)
        logger.info("execute_tools tool=%s count=%s", tool_name, len(output))

    start_dt = state.get("start")
    end_dt = state.get("end")
    candidates["paper"] = _dedupe_and_trim_papers(
        candidates.get("paper", []),
        max_items=MAX_PAPER_CANDIDATES,
        prefer_recent=bool(start_dt or end_dt),
    )

    return {"tool_results": results, "candidates": candidates}


def _parse_iso_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _dedupe_and_trim_papers(
    items: list[dict],
    *,
    max_items: int,
    prefer_recent: bool,
) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in items:
        arxiv_id = item.get("id")
        if not arxiv_id or arxiv_id in seen:
            continue
        seen.add(arxiv_id)
        deduped.append(item)

    if prefer_recent:
        def sort_key(entry: dict) -> datetime:
            updated = _parse_iso_dt(entry.get("updated"))
            published = _parse_iso_dt(entry.get("published"))
            return updated or published or datetime.min.replace(tzinfo=timezone.utc)

        deduped.sort(key=sort_key, reverse=True)

    if len(deduped) > max_items:
        deduped = deduped[:max_items]
    return deduped


def _find_keyword_windows(
    text: str,
    keywords: list[str],
    *,
    window: int,
    max_windows: int,
) -> list[str]:
    if not text or not keywords:
        return []
    lowered = text.lower()
    windows: list[str] = []
    ranges: list[tuple[int, int]] = []
    for kw in keywords:
        kw_lower = kw.lower()
        start_idx = 0
        while len(windows) < max_windows:
            idx = lowered.find(kw_lower, start_idx)
            if idx == -1:
                break
            half = window // 2
            start = max(0, idx - half)
            end = min(len(text), idx + half)
            overlaps = any(start < r_end and end > r_start for r_start, r_end in ranges)
            if not overlaps:
                windows.append(text[start:end].strip())
                ranges.append((start, end))
            start_idx = idx + len(kw_lower)
        if len(windows) >= max_windows:
            break
    return windows


def _join_windows(windows: list[str], max_chars: int) -> str:
    if not windows:
        return ""
    joined = "\n...\n".join(windows)
    if len(joined) > max_chars:
        return joined[:max_chars]
    return joined


def _read_pdfs_for_papers(state: GraphState) -> GraphState:
    candidates = state.get("candidates", {})
    papers = candidates.get("paper", [])
    pdf_max_chars = state.get("pdf_max_chars", 8000)
    fetch_budget = max(pdf_max_chars * 5, pdf_max_chars)
    fetch_budget = min(fetch_budget, 60000)
    trace_id = state.get("trace_id")
    pdf_evidence: dict[str, dict] = {}
    total_budget = max(pdf_max_chars, 4000)
    abstract_cap = max(400, min(2000, int(total_budget * 0.25)))
    method_cap = max(400, min(2000, int(total_budget * 0.25)))
    eval_cap = max(500, min(2500, int(total_budget * 0.3)))
    repro_cap = max(300, min(1200, int(total_budget * 0.2)))

    for item in papers:
        arxiv_id = item.get("id")
        if not arxiv_id:
            continue
        pdf_url = item.get("pdf_url") or _arxiv_pdf_url(arxiv_id)
        text = read_pdf_tool.invoke({"url": pdf_url, "max_chars": fetch_budget})
        summary = item.get("summary", "") or ""
        text_window = (text or "")[:60000]

        abstract_windows = _find_keyword_windows(
            text_window,
            ["abstract"],
            window=600,
            max_windows=2,
        )
        abstract_snip = _join_windows(abstract_windows, abstract_cap)
        if not abstract_snip:
            abstract_snip = summary.strip()

        method_snip = _join_windows(
            _find_keyword_windows(
                text_window,
                ["method", "approach", "model", "architecture", "algorithm"],
                window=600,
                max_windows=2,
            ),
            method_cap,
        )

        eval_snip = _join_windows(
            _find_keyword_windows(
                text_window,
                ["experiment", "evaluation", "results", "baseline", "dataset", "ablation"],
                window=650,
                max_windows=3,
            ),
            eval_cap,
        )

        repro_windows = _find_keyword_windows(
            text_window,
            ["code available", "github.com", "released", "open-source", "code release"],
            window=500,
            max_windows=2,
        )
        repro_snip = _join_windows(repro_windows, repro_cap) if repro_windows else "NOT_FOUND"

        text_snippet = (
            f"ID: {arxiv_id}\n"
            f"TITLE: {item.get('title', '')}\n"
            f"SUMMARY: {summary}\n"
            "\n"
            "ABSTRACT_EVIDENCE:\n"
            f"{abstract_snip}\n"
            "\n"
            "METHOD_EVIDENCE:\n"
            f"{method_snip}\n"
            "\n"
            "EVALUATION_EVIDENCE:\n"
            f"{eval_snip}\n"
            "\n"
            "REPRODUCIBILITY_EVIDENCE:\n"
            f"{repro_snip}\n"
        )
        pdf_evidence[arxiv_id] = {
            "pdf_url": pdf_url,
            "summary": summary,
            "text_snippet": text_snippet,
            "abstract_snip": abstract_snip,
            "method_snip": method_snip,
            "eval_snip": eval_snip,
            "repro_snip": repro_snip,
            "error": None if text else "empty_text",
        }
        log_span(
            trace_id=trace_id,
            name="read_pdf",
            input={"arxiv_id": arxiv_id, "pdf_url": pdf_url},
            output={
                "abstract_len": len(abstract_snip),
                "method_len": len(method_snip),
                "eval_len": len(eval_snip),
                "repro_len": len(repro_snip),
            },
            error=None if text else "empty_text",
            as_type="tool",
        )
        logger.info(
            "read_pdfs arxiv_id=%s abstract_len=%s method_len=%s eval_len=%s repro_len=%s",
            arxiv_id,
            len(abstract_snip),
            len(method_snip),
            len(eval_snip),
            len(repro_snip),
        )

    return {"pdf_evidence": pdf_evidence}


def _final_select(state: GraphState) -> GraphState:
    llm = _build_llm(state, temperature=0.1, max_tokens=1600)
    trace_id = state.get("trace_id")
    topic = state.get("topic", "")
    requirements = state.get("requirements") or topic
    quality_min_score = _normalize_quality_min_score(
        state.get("quality_min_score", DEFAULT_QUALITY_MIN_SCORE)
    )
    paper_rubric = _normalize_paper_rubric(state.get("paper_rubric", DEFAULT_PAPER_RUBRIC))
    candidates = state.get("candidates", {})
    pdf_evidence = state.get("pdf_evidence", {})

    paper_blocks: list[str] = []
    max_total_chars = 120000
    per_item_chars = 2800
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

    system = SystemMessage(
        content=(
            "You must output strict JSON only. "
            "Score each paper from 0-10 (one decimal allowed) using the rubric weights. "
            "Compute a weighted score as sum(item_score * weight) / sum(weights). "
            "Provide 2-4 evidence-based reasons per paper drawn from the snippets. "
            "If a paper is not relevant to the topic, give it a low score (<=3). "
            "You must return a score entry for every paper id provided."
        )
    )
    papers_text = "\n\n".join(paper_blocks)
    user = HumanMessage(
        content=(
            f"topic: {topic}\n"
            f"requirements: {requirements}\n"
            f"quality_min_score: {quality_min_score}\n"
            f"paper_rubric: {json.dumps(paper_rubric)}\n\n"
            "PAPERS:\n"
            f"{papers_text}\n\n"
            "Return JSON: {\"scores\": {\"<paper_id>\": {\"score\": 8.2, \"reasons\": [\"...\",\"...\"]}}}"
        )
    )
    response = llm.invoke([system, user])
    content = response.content or "{}"

    scores: dict[str, dict] = {}
    payload = _load_json_with_repair(content) or {}
    raw_scores = payload.get("scores", {})
    if isinstance(raw_scores, dict):
        for paper_id, entry in raw_scores.items():
            if not isinstance(entry, dict):
                continue
            try:
                score_value = float(entry.get("score", 0))
            except (TypeError, ValueError):
                score_value = 0.0
            reasons = entry.get("reasons", [])
            if not isinstance(reasons, list):
                reasons = []
            reasons = [str(r) for r in reasons if r]
            scores[str(paper_id)] = {"score": score_value, "reasons": reasons}

    valid_ids = {item.get("id") for item in candidates.get("paper", [])}
    scores = {pid: entry for pid, entry in scores.items() if pid in valid_ids}

    paper_reasons: dict[str, list[str]] = {}
    selected_ids: list[str] = []
    for item in candidates.get("paper", []):
        arxiv_id = item.get("id")
        if not arxiv_id:
            continue
        entry = scores.get(arxiv_id, {})
        score_value = entry.get("score", 0.0)
        if not isinstance(score_value, (int, float)):
            score_value = 0.0
        if score_value >= quality_min_score:
            selected_ids.append(arxiv_id)
        paper_reasons[arxiv_id] = entry.get("reasons", []) if isinstance(entry, dict) else []

    selected = {"paper": selected_ids, "blog": [], "news": []}

    logger.info(
        "final_select selected paper=%s (scored=%s)",
        len(selected["paper"]),
        len(scores),
    )
    final_input = {
        "topic": topic,
        "requirements": requirements,
        "quality_min_score": quality_min_score,
        "paper_rubric": paper_rubric,
        "paper_content": papers_text[:500],
        "paper_count": len(candidates.get("paper", [])),
        "paper_ids": [item.get("id") for item in candidates.get("paper", [])],
        "prompt_chars": len(system.content) + len(user.content),
    }
    logger.info("final_select langfuse_input=%s", final_input)
    usage = getattr(response, "response_metadata", {}).get("token_usage")
    log_generation(
        trace_id=trace_id,
        name="final_select",
        model=llm.model_name,
        input=final_input,
        output={"scores": scores, "selected": selected},
        usage=usage,
    )
    return {
        "selected": selected,
        "paper_scores": scores,
        "paper_reasons": paper_reasons,
    }


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
    trace_id = state.get("trace_id")
    if not papers:
        logger.info("store_papers no valuable papers to save")
        log_span(
            trace_id=trace_id,
            name="store_papers",
            input={"count": 0},
            output={"stored": 0},
        )
        return {"stored_papers": []}
    stored = store_papers(papers, _paper_dir())
    _export_selected_pdfs(stored)
    logger.info("store_papers stored=%s", len(stored))
    log_span(
        trace_id=trace_id,
        name="store_papers",
        input={"count": len(papers)},
        output={"stored": len(stored)},
    )
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
    requirements: str,
    content_type: ContentType,
    start: datetime | None,
    end: datetime | None,
    tz: str,
    iflow_key: str | None,
    iflow_base_url: str | None,
    iflow_model: str | None,
    session_id: str | None,
    max_results: int,
    pdf_max_chars: int,
) -> GraphResult:
    if content_type not in ("paper", "all", "news", "blog"):
        return GraphResult(stored_papers=0)
    graph = build_graph().compile()
    trace_id = start_trace(
        name="signalforge_daily_run",
        input={"topic": topic, "requirements": requirements, "content_type": content_type},
        session_id=session_id,
    )
    logger.info("trace_id=%s", trace_id)
    init_state = {
        "topic": topic,
        "requirements": requirements or topic,
        "content_type": content_type,
        "start": start,
        "end": end,
        "timezone": tz,
        "iflow_key": iflow_key,
        "iflow_base_url": iflow_base_url,
        "iflow_model": iflow_model,
        "session_id": session_id,
        "trace_id": trace_id,
        "max_results": max_results,
        "pdf_max_chars": pdf_max_chars,
        "search_query": "",
        "must_mention": [],
        "plan": [],
        "tool_results": {},
        "candidates": {"paper": [], "blog": [], "news": []},
        "pdf_evidence": {},
        "selected": {"paper": [], "blog": [], "news": []},
        "quality_min_score": DEFAULT_QUALITY_MIN_SCORE,
        "paper_rubric": list(DEFAULT_PAPER_RUBRIC),
        "paper_scores": {},
        "paper_reasons": {},
        "valuable_papers": [],
        "stored_papers": [],
    }
    result = graph.invoke(init_state)
    update_trace_name(
        trace_id,
        name="signalforge_daily_run",
        session_id=session_id,
        input={"topic": topic, "requirements": requirements, "content_type": content_type},
    )
    flush()
    return GraphResult(stored_papers=len(result.get("stored_papers", [])))


def _paper_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "paper"


def _cached_pdf_path(pdf_url: str) -> Path:
    filename = pdf_url.split("/")[-1]
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    return _paper_dir() / "pdf_cache" / filename


def _export_selected_pdfs(entries: list[ArxivEntry]) -> None:
    if not entries:
        return
    dest_dir = _paper_dir() / "pdfs"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        pdf_url = _arxiv_pdf_url(entry.arxiv_id)
        cache_path = _cached_pdf_path(pdf_url)
        if not cache_path.exists():
            logger.warning("export_pdfs missing_cache arxiv_id=%s", entry.arxiv_id)
            continue
        dest_path = dest_dir / cache_path.name
        try:
            shutil.copy2(cache_path, dest_path)
        except OSError as exc:
            logger.warning("export_pdfs failed arxiv_id=%s err=%s", entry.arxiv_id, exc)


def _arxiv_pdf_url(arxiv_id: str) -> str:
    if "/abs/" in arxiv_id:
        return arxiv_id.replace("/abs/", "/pdf/") + ".pdf"
    if arxiv_id.endswith(".pdf"):
        return arxiv_id
    return arxiv_id + ".pdf"
