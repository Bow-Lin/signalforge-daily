from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

from .digest import (
    FeedSource,
    RelevanceProfile,
    SourceConfig,
    default_relevance_profile,
    feed_sources_from_configs,
    load_default_feed_sources,
    run_digest,
)


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
    parser.add_argument("--sources-config", help="Optional SourceConfig JSON file")
    parser.add_argument("--relevance-profile", help="Optional RelevanceProfile JSON file")
    parser.add_argument("--source-stats-output", help="Write SourceRunStat JSON to this path")
    parser.add_argument("--run-id", default="", help="Run id for per-source stats")

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


def _load_sources_config(path: str) -> list[SourceConfig]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload if isinstance(payload, list) else payload.get("sources", [])
    configs: list[SourceConfig] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        configs.append(
            SourceConfig(
                id=str(row.get("id", "")).strip(),
                name=str(row.get("name", "")).strip() or str(row.get("url", "")).strip(),
                type=row.get("type", "rss"),
                url=str(row.get("url", "")).strip(),
                enabled=bool(row.get("enabled", True)),
                tags=[str(item).strip() for item in row.get("tags", []) if str(item).strip()],
                priority=row.get("priority", "normal"),
                created_at=str(row.get("createdAt") or row.get("created_at") or ""),
                updated_at=str(row.get("updatedAt") or row.get("updated_at") or ""),
            )
        )
    return configs


def _load_relevance_profile(path: str, lang: str) -> RelevanceProfile:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return default_relevance_profile(lang if lang in {"zh", "en"} else "zh")
    return RelevanceProfile(
        interested_topics=[str(item).strip() for item in payload.get("interestedTopics", []) if str(item).strip()],
        muted_topics=[str(item).strip() for item in payload.get("mutedTopics", []) if str(item).strip()],
        preferred_content_types=[
            str(item).strip()
            for item in payload.get("preferredContentTypes", [])
            if str(item).strip()
        ],
        language=payload.get("language", "mixed"),
    )


def _camel_source_stat(stat) -> dict:
    row = asdict(stat)
    return {
        "runId": row["run_id"],
        "sourceId": row["source_id"],
        "sourceName": row["source_name"],
        "sourceType": row["source_type"],
        "enabled": row["enabled"],
        "fetchedCount": row["fetched_count"],
        "candidateCount": row["candidate_count"],
        "selectedCount": row["selected_count"],
        "status": row["status"],
        "errorType": row["error_type"],
        "errorMessage": row["error_message"],
        "startedAt": row["started_at"],
        "finishedAt": row["finished_at"],
        "durationMs": row["duration_ms"],
    }


def main() -> int:
    load_dotenv()
    args = _parse_args()
    _setup_logging(args.log_level)

    source_configs = _load_sources_config(args.sources_config) if args.sources_config else None
    if args.feeds_file:
        feeds = _load_custom_feeds(args.feeds_file)
    elif source_configs is not None:
        feeds = feed_sources_from_configs(source_configs)
    else:
        feeds = load_default_feed_sources()
    relevance_profile = (
        _load_relevance_profile(args.relevance_profile, args.lang)
        if args.relevance_profile
        else None
    )

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
        source_configs=source_configs,
        relevance_profile=relevance_profile,
        run_id=args.run_id,
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

    if args.source_stats_output:
        output = Path(args.source_stats_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps([_camel_source_stat(stat) for stat in result.source_run_stats], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
