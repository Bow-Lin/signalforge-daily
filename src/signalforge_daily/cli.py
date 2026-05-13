from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path

from .graph import ContentType, run_collection


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect topic-related content.")
    parser.add_argument("--config", help="Path to JSON config file.")
    parser.add_argument("--topic", help="Topic to search.")
    parser.add_argument("--requirements", help="Search constraints/requirements.")
    parser.add_argument(
        "--content-type",
        choices=["paper", "news", "blog", "all"],
        help="Content type to collect.",
    )
    parser.add_argument("--start", help="Start time (YYYY-MM-DD or ISO).")
    parser.add_argument("--end", help="End time (YYYY-MM-DD or ISO).")
    parser.add_argument("--tz", help="Timezone name (e.g. Asia/Shanghai).")
    parser.add_argument("--iflow-key", help="iFlow API key (or set IFLOW_API_KEY).")
    parser.add_argument("--iflow-base-url")
    parser.add_argument("--iflow-model")
    parser.add_argument("--max-results", type=int)
    parser.add_argument("--pdf-max-chars", type=int)
    parser.add_argument("--log-level")
    parser.add_argument("--session-id")
    return parser.parse_args()


def _load_config(path: str | None) -> dict:
    if not path:
        return {}
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config not found: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _get_value(args: argparse.Namespace, config: dict, key: str, default=None):
    value = getattr(args, key, None)
    if value is not None:
        return value
    return config.get(key, default)


def main() -> int:
    args = _parse_args()
    config = _load_config(args.config)
    log_level = _get_value(args, config, "log_level", "INFO")
    if isinstance(log_level, int):
        level = log_level
    else:
        level = getattr(logging, str(log_level).upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    topic = _get_value(args, config, "topic")
    if not topic:
        raise ValueError("topic is required (use --topic or config file)")
    requirements = _get_value(args, config, "requirements")
    if requirements is None:
        requirements = topic

    start_str = _get_value(args, config, "start")
    end_str = _get_value(args, config, "end")
    tz_name = _get_value(args, config, "tz", "UTC")
    start: datetime | None = None
    end: datetime | None = None
    if start_str:
        dt = datetime.fromisoformat(start_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        start = dt
    if end_str:
        dt = datetime.fromisoformat(end_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        end = dt

    result = run_collection(
        topic=topic,
        requirements=requirements,
        content_type=_get_value(args, config, "content_type", "paper"),
        start=start,
        end=end,
        tz=tz_name,
        iflow_key=_get_value(args, config, "iflow_key", args.iflow_key),
        iflow_base_url=_get_value(args, config, "iflow_base_url", "https://apis.iflow.cn/v1"),
        iflow_model=_get_value(args, config, "iflow_model", "qwen3-coder-plus"),
        session_id=_get_value(args, config, "session_id", args.session_id),
        max_results=_get_value(args, config, "max_results", 5),
        pdf_max_chars=_get_value(args, config, "pdf_max_chars", 16000),
    )
    print(f"stored_papers={result.stored_papers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
