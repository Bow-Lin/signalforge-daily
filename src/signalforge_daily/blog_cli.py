from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from typing import Callable

from dotenv import load_dotenv

from .blog_tracker import BlogTracker, Storage


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Track blog updates.")
    parser.add_argument("--sources-path", default="blog/sources.txt")
    parser.add_argument("--data-dir", default="blog")
    parser.add_argument(
        "--source",
        action="append",
        choices=["claude", "lilian", "openai", "all"],
        help="Blog source(s) to sync. Repeatable. Default: all",
    )
    parser.add_argument("--claude-url", default="https://claude.com/blog")
    parser.add_argument("--lilian-url", default="https://lilianweng.github.io/")
    parser.add_argument("--openai-url", default="https://developers.openai.com/blog/")
    parser.add_argument("--iflow-key")
    parser.add_argument("--iflow-base-url")
    parser.add_argument("--iflow-model")
    parser.add_argument("--session-id")
    parser.add_argument("--summary-max-input-chars", type=int, default=8000)
    parser.add_argument("--summary-max-tokens", type=int, default=400)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--no-summaries", action="store_true")
    return parser.parse_args()


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _resolve_sources(raw: list[str] | None) -> list[str]:
    if not raw:
        return ["claude", "lilian", "openai"]
    if "all" in raw:
        return ["claude", "lilian", "openai"]
    return raw


def _print_result(result, show_summaries: bool) -> None:
    print(
        f"blog={result.blog_url} new_or_updated={result.new_or_updated} "
        f"saved={len(result.saved)} since={result.since}"
    )
    if show_summaries and result.summaries:
        for url, summary in result.summaries.items():
            print(f"- {url}\n  {summary}")


def _ensure_default_sources(storage: Storage) -> None:
    meta = storage.get_last_run_at()
    if meta == "last_run_at":
        storage.update_last_run_at("")
    existing = storage.list_sources()
    if existing:
        return
    lines = [
        "last_run_at",
        "Claude Blog\thttps://claude.com/blog",
        "Lilian Weng Blog\thttps://lilianweng.github.io/",
        "OpenAI Developers Blog\thttps://developers.openai.com/blog/",
    ]
    storage.sources_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    load_dotenv()
    args = _parse_args()
    _setup_logging(args.log_level)

    storage = Storage(args.sources_path)
    _ensure_default_sources(storage)
    sources = _resolve_sources(args.source)
    defer_last_run = len(sources) > 1
    tracker = BlogTracker(
        storage=storage,
        data_dir=args.data_dir,
        iflow_key=args.iflow_key,
        iflow_base_url=args.iflow_base_url,
        iflow_model=args.iflow_model,
        session_id=args.session_id,
        defer_last_run_at=defer_last_run,
        summary_max_input_chars=args.summary_max_input_chars,
        summary_max_tokens=args.summary_max_tokens,
    )
    runners: dict[str, Callable[[], object]] = {
        "claude": lambda: tracker.sync_claude_blog(args.claude_url),
        "lilian": lambda: tracker.sync_lilian_weng_blog(args.lilian_url),
        "openai": lambda: tracker.sync_openai_blog(args.openai_url),
    }

    show_summaries = not args.no_summaries
    success_count = 0
    for source in sources:
        runner = runners.get(source)
        if runner is None:
            continue
        try:
            result = runner()
        except Exception as exc:
            logging.getLogger(__name__).warning("sync failed source=%s err=%s", source, exc)
            continue
        _print_result(result, show_summaries)
        success_count += 1

    if defer_last_run and success_count > 0:
        storage.update_last_run_at(datetime.now(timezone.utc).isoformat())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
