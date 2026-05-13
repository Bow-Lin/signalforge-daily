from __future__ import annotations

import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv

from .digest import FeedSource, load_default_feed_sources, run_digest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate AI daily digest from RSS feeds.")
    parser.add_argument("--hours", type=int, default=48, help="Time range in hours (default: 48)")
    parser.add_argument("--top-n", type=int, default=15, help="Top N articles to include (default: 15)")
    parser.add_argument("--lang", choices=["zh", "en"], default="zh", help="Summary language")
    parser.add_argument("--output", help="Output markdown path (default: ./output/digest-YYYYMMDD.md)")

    parser.add_argument("--iflow-key")
    parser.add_argument("--iflow-base-url")
    parser.add_argument("--iflow-model")

    parser.add_argument("--feed-timeout", type=int, default=15, help="Single feed fetch timeout seconds")
    parser.add_argument("--feed-concurrency", type=int, default=10, help="Feed fetch concurrency")
    parser.add_argument("--ai-batch-size", type=int, default=10, help="AI batch size")
    parser.add_argument("--ai-retries", type=int, default=1, help="AI retry count")
    parser.add_argument("--max-ai-articles", type=int, default=120, help="Cap article count sent to AI")
    parser.add_argument(
        "--feeds-file",
        help="Optional custom feed list file, each line: name<TAB>rss_url (or just rss_url)",
    )

    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, str(level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _load_custom_feeds(path: str) -> list[FeedSource]:
    feeds: list[FeedSource] = []
    raw = Path(path).read_text(encoding="utf-8")
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            name, xml_url = parts[0].strip(), parts[1].strip()
        else:
            xml_url = parts[0].strip()
            name = xml_url
        if not xml_url:
            continue
        feeds.append(FeedSource(name=name or xml_url, xml_url=xml_url))
    return feeds


def main() -> int:
    load_dotenv()
    args = _parse_args()
    _setup_logging(args.log_level)

    feeds = _load_custom_feeds(args.feeds_file) if args.feeds_file else load_default_feed_sources()

    print("[digest] === AI Daily Digest (Python) ===")
    print(f"[digest] Time range: {args.hours} hours")
    print(f"[digest] Top N: {args.top_n}")
    print(f"[digest] Language: {args.lang}")
    print(f"[digest] Feed sources: {len(feeds)}")
    if args.output:
        print(f"[digest] Output: {args.output}")

    result = run_digest(
        hours=args.hours,
        top_n=args.top_n,
        lang=args.lang,
        output_path=args.output,
        iflow_key=args.iflow_key,
        iflow_base_url=args.iflow_base_url,
        iflow_model=args.iflow_model,
        feed_timeout_s=args.feed_timeout,
        feed_concurrency=args.feed_concurrency,
        ai_batch_size=args.ai_batch_size,
        ai_retries=args.ai_retries,
        max_ai_articles=args.max_ai_articles,
        feeds=feeds,
    )

    print("[digest] Done!")
    print(f"[digest] Report: {result.output_path}")
    print(
        "[digest] Stats: "
        f"{result.stats.success_feeds} sources -> {result.stats.total_articles} articles "
        f"-> {result.stats.filtered_articles} recent -> {len(result.articles)} selected"
    )

    if result.articles:
        print("[digest] Top 3 Preview:")
        for idx, article in enumerate(result.articles[:3], start=1):
            print(f"  {idx}. {article.title_zh or article.title}")
            print(f"     {article.summary[:80]}...")

    if result.fetch_failures:
        print(f"[digest] Feed failures: {len(result.fetch_failures)}")
        for name, reason in sorted(result.fetch_failures.items()):
            print(f"[digest] Feed failure: {name} | {reason}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
