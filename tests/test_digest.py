from __future__ import annotations

from datetime import datetime, timezone

from news_collection.digest import (
    DigestStats,
    ScoreBreakdown,
    ScoredArticle,
    _extract_response_text,
    generate_digest_report,
    parse_feed_items,
    parse_json_response,
)


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
    )
    stats = DigestStats(
        total_feeds=92,
        success_feeds=90,
        total_articles=200,
        filtered_articles=20,
        hours=24,
    )
    report = generate_digest_report([article, article, article], "今日看点", stats)
    assert "## 🏆 今日必读" in report
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
