"""collectors.hatena._parse() のユニットテスト"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.hatena import _parse

NOW = "2026-01-01T00:00:00+00:00"
XML = """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/"
 xmlns:hatena="http://www.hatena.ne.jp/info/xmlns#">
<item><title>記事A</title><link>https://example.com/a</link><hatena:bookmarkcount>123</hatena:bookmarkcount></item>
<item><title>記事B</title><link>https://example.com/b</link></item>
<item><title></title><link>https://example.com/c</link></item>
</rdf:RDF>"""


def test_parse_score_and_skip_incomplete():
    posts = _parse(XML, NOW)
    assert [(p.title, p.score, p.source) for p in posts] == [("記事A", 123, "hatena"), ("記事B", 0, "hatena")]
    assert posts[0].discussion_url == "https://b.hatena.ne.jp/entry/https://example.com/a"


def test_parse_invalid_xml_returns_empty():
    assert _parse("<rdf", NOW) == []
