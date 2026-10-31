"""collectors.zenn._parse() のユニットテスト"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.zenn import _feed_url, _parse

NOW = "2026-01-01T00:00:00+00:00"
XML = """<?xml version="1.0"?><rss version="2.0"><channel>
<item><title><![CDATA[記事A]]></title><link>https://zenn.dev/u/articles/a</link></item>
<item><title></title><link>https://zenn.dev/u/articles/b</link></item>
<item><title>記事C</title></item>
</channel></rss>"""


def test_parse_skips_incomplete_items():
    posts = _parse(XML, NOW)
    got = [(p.title, p.url, p.source, p.score) for p in posts]
    assert got == [("記事A", "https://zenn.dev/u/articles/a", "zenn", 0)]


def test_parse_invalid_xml_returns_empty():
    assert _parse("<rss", NOW) == []


def test_feed_url():
    assert _feed_url("") == "https://zenn.dev/feed"
    assert _feed_url("llm") == "https://zenn.dev/topics/llm/feed"
