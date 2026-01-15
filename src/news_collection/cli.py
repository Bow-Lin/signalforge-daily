from __future__ import annotations

import argparse
from datetime import datetime
import logging

from .graph import ContentType, run_collection
from datetime import timezone


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect topic-related content.")
    parser.add_argument("--topic", required=True, help="Topic to search.")
    parser.add_argument(
        "--content-type",
        choices=["paper", "news", "blog", "all"],
        default="paper",
        help="Content type to collect.",
    )
    parser.add_argument("--start", help="Start time (YYYY-MM-DD or ISO).")
    parser.add_argument("--end", help="End time (YYYY-MM-DD or ISO).")
    parser.add_argument("--tz", default="UTC", help="Timezone name (e.g. Asia/Shanghai).")
    parser.add_argument("--iflow-key", help="iFlow API key (or set IFLOW_API_KEY).")
    parser.add_argument("--iflow-base-url", default="https://apis.iflow.cn/v1")
    parser.add_argument("--iflow-model", default="qwen3-coder-plus")
    parser.add_argument("--max-results", type=int, default=50)
    parser.add_argument("--pdf-max-chars", type=int, default=16000)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    start: datetime | None = None
    end: datetime | None = None
    if args.start:
        dt = datetime.fromisoformat(args.start)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        start = dt
    if args.end:
        dt = datetime.fromisoformat(args.end)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        end = dt

    result = run_collection(
        topic=args.topic,
        content_type=args.content_type,
        start=start,
        end=end,
        tz=args.tz,
        iflow_key=args.iflow_key,
        iflow_base_url=args.iflow_base_url,
        iflow_model=args.iflow_model,
        max_results=args.max_results,
        pdf_max_chars=args.pdf_max_chars,
    )
    print(f"stored_papers={result.stored_papers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
