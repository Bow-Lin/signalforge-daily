from __future__ import annotations

from datetime import datetime, timezone

from signalforge_daily.digest import (
    Article,
    DigestStats,
    FeedSource,
    QualitySummary,
    RelevanceProfile,
    ScoreBreakdown,
    ScoredArticle,
    _dedupe_articles,
    apply_relevance_profile,
    build_scoring_prompt,
    feed_sources_from_configs,
    _extract_response_text,
    fetch_all_feeds,
    generate_digest_report,
    load_default_feed_sources,
    parse_feed_items,
    parse_json_response,
    SourceConfig,
)
from signalforge_daily.blog_tracker.sources.base import ListedPost


def test_parse_json_response_with_code_fence() -> None:
    text = '```json\n{"results": [{"index": 0, "relevance": 8}]}\n```'
    payload = parse_json_response(text)
    assert payload["results"][0]["index"] == 0


def test_parse_rss_items() -> None:
    xml = """
    <rss version="2.0">
      <channel>
        <item>
          <title>Hello RSS</title>
          <link>https://example.com/a</link>
          <pubDate>Wed, 25 Feb 2026 08:00:00 GMT</pubDate>
          <description><![CDATA[<p>RSS body</p>]]></description>
        </item>
      </channel>
    </rss>
    """
    items = parse_feed_items(xml, source_name="example", source_url="https://example.com/rss")
    assert len(items) == 1
    assert items[0].title == "Hello RSS"
    assert items[0].description == "RSS body"


def test_parse_atom_items() -> None:
    xml = """
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Hello Atom</title>
        <link rel="alternate" href="https://example.com/b" />
        <updated>2026-02-25T08:00:00Z</updated>
        <summary>Atom body</summary>
      </entry>
    </feed>
    """
    items = parse_feed_items(xml, source_name="example", source_url="https://example.com/atom")
    assert len(items) == 1
    assert items[0].link == "https://example.com/b"
    assert items[0].description == "Atom body"


def test_dedupe_articles_uses_normalized_title_across_sources() -> None:
    older = Article(
        title="Same Launch",
        link="https://source-a.example.com/posts/same-launch",
        pub_date=datetime(2026, 2, 25, 8, 0, 0, tzinfo=timezone.utc),
        description="Older duplicate",
        source_name="source-a",
        source_url="https://source-a.example.com/rss",
    )
    newer = Article(
        title="  Same   Launch  ",
        link="https://source-b.example.com/news/same-launch",
        pub_date=datetime(2026, 2, 25, 9, 0, 0, tzinfo=timezone.utc),
        description="Newer duplicate",
        source_name="source-b",
        source_url="https://source-b.example.com/rss",
    )
    distinct = Article(
        title="Different Launch",
        link="https://source-c.example.com/news/different-launch",
        pub_date=datetime(2026, 2, 25, 7, 0, 0, tzinfo=timezone.utc),
        description="Different article",
        source_name="source-c",
        source_url="https://source-c.example.com/rss",
    )

    items = _dedupe_articles([older, newer, distinct])

    assert len(items) == 2
    assert items[0].link == "https://source-b.example.com/news/same-launch"
    assert items[1].link == "https://source-c.example.com/news/different-launch"


def test_disabled_source_config_is_not_fetched() -> None:
    sources = feed_sources_from_configs(
        [
            SourceConfig(
                id="enabled",
                name="Enabled Source",
                type="rss",
                url="https://example.com/enabled.xml",
                enabled=True,
            ),
            SourceConfig(
                id="disabled",
                name="Disabled Source",
                type="rss",
                url="https://example.com/disabled.xml",
                enabled=False,
            ),
        ]
    )

    assert [source.name for source in sources] == ["Enabled Source"]


def test_relevance_profile_filters_muted_topics_and_enters_prompt() -> None:
    article = Article(
        title="Funding news for agent startup",
        link="https://example.com/funding",
        pub_date=datetime(2026, 2, 25, 8, 0, 0, tzinfo=timezone.utc),
        description="Series A funding update",
        source_name="example",
        source_url="https://example.com/rss",
    )
    profile = RelevanceProfile(
        interested_topics=["agent"],
        muted_topics=["funding"],
        preferred_content_types=["engineering_blog"],
        language="zh",
    )

    assert apply_relevance_profile([article], profile) == []
    prompt = build_scoring_prompt([(0, article)], profile)
    assert "agent" in prompt
    assert "funding" in prompt
    assert "engineering_blog" in prompt


def test_generate_digest_report_contains_sections() -> None:
    article = ScoredArticle(
        title="Original",
        link="https://example.com/original",
        pub_date=datetime(2026, 2, 25, 8, 0, 0, tzinfo=timezone.utc),
        description="desc",
        source_name="example",
        source_url="https://example.com/rss",
        score_breakdown=ScoreBreakdown(8, 7, 9),
        category="engineering",
        keywords=["python", "rss"],
        title_zh="中文标题",
        summary="摘要内容",
        reason="推荐理由",
        matched_topics=["python"],
        content_type="engineering_blog",
        relevance_score=24,
    )
    stats = DigestStats(
        total_feeds=92,
        success_feeds=90,
        total_articles=200,
        filtered_articles=20,
        hours=24,
    )
    quality = QualitySummary(
        sources_scanned=92,
        articles_fetched=200,
        candidates_after_filtering=20,
        selected_count=3,
        top_matched_topics=[("python", 3)],
        noisy_sources=["noisy"],
        failed_sources=["broken"],
    )
    report = generate_digest_report([article, article, article], "今日看点", stats, quality)
    assert "## 🏆 今日必读" in report
    assert "## Quality Summary" in report
    assert "Why selected" in report
    assert "Matched topics" in report
    assert "## 📊 数据概览" in report
    assert "中文标题" in report


def test_extract_response_text_handles_none_message() -> None:
    class _Resp:
        choices = [None]

    assert _extract_response_text(_Resp()) == ""


def test_extract_response_text_from_model_dump() -> None:
    class _Resp:
        choices = None

        @staticmethod
        def model_dump() -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "text", "text": "hello"},
                            ]
                        }
                    }
                ]
            }

    assert _extract_response_text(_Resp()) == "hello"


def test_load_default_feed_sources_includes_official_ai_dev_blogs() -> None:
    sources = {source.name: source for source in load_default_feed_sources()}

    assert sources["OpenAI Developers Blog"].source_type == "openai_blog"
    assert sources["Claude Blog"].source_type == "claude_blog"


def test_fetch_all_feeds_supports_openai_blog_sources(monkeypatch) -> None:
    now = datetime(2026, 3, 20, 8, 0, 0, tzinfo=timezone.utc)

    class _FakeOpenAIClient:
        def __init__(self, base_url: str, timeout_s: int = 30) -> None:
            self.base_url = base_url
            self.timeout_s = timeout_s

        def list_posts(self, since: datetime) -> list[ListedPost]:
            assert since <= now
            return [
                ListedPost(
                    url="https://developers.openai.com/blog/test-post",
                    title="Test Post",
                    published_at=now,
                )
            ]

        def fetch_html(self, url: str) -> str:
            assert url == "https://developers.openai.com/blog/test-post"
            return "<html><body><article><p>OpenAI blog body.</p></article></body></html>"

    monkeypatch.setattr("signalforge_daily.digest.OpenAIDevBlogClient", _FakeOpenAIClient)

    articles, stats = fetch_all_feeds(
        [
            FeedSource(
                name="OpenAI Developers Blog",
                xml_url="https://developers.openai.com/blog/",
                source_type="openai_blog",
            )
        ],
        timeout_s=5,
        concurrency=1,
    )

    assert stats.success_feeds == 1
    assert len(articles) == 1
    assert articles[0].title == "Test Post"
    assert articles[0].description == "OpenAI blog body."
    assert stats.source_stats[0].source_name == "OpenAI Developers Blog"
