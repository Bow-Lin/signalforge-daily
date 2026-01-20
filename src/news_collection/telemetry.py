from __future__ import annotations

from typing import Any, Optional
import os
import logging


_langfuse_client = None
_dotenv_loaded = False
_logged_missing = False
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
) -> Optional[str]:
    client = get_langfuse()
    if not client:
        return None
    try:
        trace_id = client.create_trace_id()
        span = client.start_span(
            trace_context={"trace_id": trace_id},
            name=name,
            input=input,
            metadata=metadata,
        )
        try:
            span.update_trace(
                name=name,
                input=input,
                metadata=metadata,
                session_id=session_id,
            )
        except Exception:
            pass
        span.end()
        logger.info("langfuse trace started trace_id=%s", trace_id)
        return trace_id
    except Exception:
        logger.warning("langfuse trace start failed", exc_info=True)
        return None


def log_span(
    trace_id: Optional[str],
    name: str,
    input: Any | None = None,
    output: Any | None = None,
    metadata: dict | None = None,
    error: str | None = None,
    as_type: str = "span",
) -> None:
    client = get_langfuse()
    if not client or not trace_id:
        return
    try:
        obs = client.start_observation(
            trace_context={"trace_id": trace_id},
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
) -> None:
    client = get_langfuse()
    if not client or not trace_id:
        return
    try:
        gen = client.start_observation(
            trace_context={"trace_id": trace_id},
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


def update_trace_name(
    trace_id: Optional[str],
    name: str,
    session_id: Optional[str] = None,
    input: Any | None = None,
    metadata: dict | None = None,
) -> None:
    client = get_langfuse()
    if not client or not trace_id:
        return
    try:
        span = client.start_span(
            trace_context={"trace_id": trace_id},
            name=name,
            input=input,
            metadata=metadata,
        )
        try:
            span.update_trace(
                name=name,
                input=input,
                metadata=metadata,
                session_id=session_id,
            )
        except Exception:
            pass
        span.end()
    except Exception:
        return
