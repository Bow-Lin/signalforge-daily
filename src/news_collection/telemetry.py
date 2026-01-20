from __future__ import annotations

from typing import Any, Optional
import os
import logging


_langfuse_client = None
_dotenv_loaded = False
_logged_missing = False
_root_spans: dict[str, object] = {}
_trace_meta: dict[str, dict] = {}
logger = logging.getLogger(__name__)


def _init_langfuse() -> Optional["Langfuse"]:
    global _dotenv_loaded
    if not _dotenv_loaded:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except Exception:
            pass
        _dotenv_loaded = True

    try:
        from langfuse import Langfuse
    except Exception:
        return None

    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
    host = os.environ.get("LANGFUSE_HOST", "").strip() or None
    if not public_key or not secret_key:
        global _logged_missing
        if not _logged_missing:
            logging.getLogger(__name__).info(
                "langfuse not configured (missing LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY)"
            )
            _logged_missing = True
        return None

    kwargs = {"public_key": public_key, "secret_key": secret_key}
    if host:
        kwargs["host"] = host
    return Langfuse(**kwargs)


def get_langfuse() -> Optional["Langfuse"]:
    global _langfuse_client
    if _langfuse_client is None:
        _langfuse_client = _init_langfuse()
    return _langfuse_client


def start_trace(
    name: str,
    input: Any | None = None,
    metadata: dict | None = None,
    session_id: str | None = None,
) -> tuple[Optional[str], Optional[str]]:
    client = get_langfuse()
    if not client:
        return None, None
    try:
        trace_id = client.create_trace_id()
        span = client.start_span(
            trace_context={"trace_id": trace_id},
            name=name,
            input=input,
            metadata=metadata,
        )
        _root_spans[trace_id] = span
        _trace_meta[trace_id] = {
            "name": name,
            "input": input,
            "metadata": metadata,
            "session_id": session_id,
        }
        try:
            span.update_trace(
                name=name,
                input=input,
                metadata=metadata,
                session_id=session_id,
            )
        except Exception:
            pass
        try:
            trace_url = client.get_trace_url(trace_id)
        except Exception:
            trace_url = None
        logger.info(
            "langfuse trace started trace_id=%s span_id=%s trace_url=%s",
            trace_id,
            span.id,
            trace_url,
        )
        return trace_id, span.id
    except Exception:
        logger.warning("langfuse trace start failed", exc_info=True)
        return None, None


def log_span(
    trace_id: Optional[str],
    name: str,
    input: Any | None = None,
    output: Any | None = None,
    metadata: dict | None = None,
    error: str | None = None,
    as_type: str = "span",
    parent_span_id: Optional[str] = None,
) -> None:
    client = get_langfuse()
    if not client or not trace_id:
        return
    try:
        trace_context = {"trace_id": trace_id}
        if parent_span_id:
            trace_context["parent_span_id"] = parent_span_id
        obs = client.start_observation(
            trace_context=trace_context,
            name=name,
            as_type=as_type,
            input=input,
            output=output,
            metadata=metadata,
            level="ERROR" if error else "DEFAULT",
            status_message=error,
        )
        obs.end()
    except Exception:
        return


def log_generation(
    trace_id: Optional[str],
    name: str,
    model: str,
    input: Any | None = None,
    output: Any | None = None,
    usage: dict | None = None,
    metadata: dict | None = None,
    error: str | None = None,
    parent_span_id: Optional[str] = None,
) -> None:
    client = get_langfuse()
    if not client or not trace_id:
        return
    try:
        trace_context = {"trace_id": trace_id}
        if parent_span_id:
            trace_context["parent_span_id"] = parent_span_id
        gen = client.start_observation(
            trace_context=trace_context,
            name=name,
            as_type="generation",
            input=input,
            output=output,
            metadata=metadata,
            model=model,
            usage_details=usage,
            level="ERROR" if error else "DEFAULT",
            status_message=error,
        )
        gen.end()
    except Exception:
        return


def flush() -> None:
    client = get_langfuse()
    if not client:
        return
    try:
        client.flush()
    except Exception:
        return


def get_trace_url(trace_id: Optional[str]) -> Optional[str]:
    client = get_langfuse()
    if not client or not trace_id:
        return None
    try:
        return client.get_trace_url(trace_id)
    except Exception:
        return None


def end_trace(trace_id: Optional[str]) -> None:
    if not trace_id:
        return
    span = _root_spans.pop(trace_id, None)
    if not span:
        return
    try:
        meta = _trace_meta.pop(trace_id, {})
        if meta:
            try:
                span.update_trace(
                    name=meta.get("name"),
                    input=meta.get("input"),
                    metadata=meta.get("metadata"),
                    session_id=meta.get("session_id"),
                )
            except Exception:
                pass
        span.end()
    except Exception:
        return


def session_context(session_id: Optional[str]):
    try:
        from langfuse import propagate_attributes
    except Exception:
        class _Noop:
            def __enter__(self):
                return None
            def __exit__(self, exc_type, exc, tb):
                return False
        return _Noop()

    if not session_id:
        class _Noop:
            def __enter__(self):
                return None
            def __exit__(self, exc_type, exc, tb):
                return False
        return _Noop()

    return propagate_attributes(session_id=session_id)
