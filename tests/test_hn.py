"""collectors.hn._parse() のユニットテスト"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.hn import _parse

NOW = "2026-01-01T00:00:00+00:00"


def test_parse_basic():
    posts = _parse([{"objectID": "1", "title": "T", "url": "https://x.dev/a", "points": 42}], NOW)
    assert len(posts) == 1
    p = posts[0]
    assert (p.url, p.title, p.score, p.source) == ("https://x.dev/a", "T", 42, "hn")
    assert p.discussion_url == "https://news.ycombinator.com/item?id=1"


def test_ask_hn_without_url_falls_back_to_discussion():
    p = _parse([{"objectID": "2", "title": "Ask HN: q", "points": None}], NOW)[0]
    assert p.url == p.discussion_url
    assert p.score == 0


def test_skips_missing_title_or_id():
    assert _parse([{"objectID": "3"}, {"title": "x"}], NOW) == []


def test_point_id_stable_per_url():
    a, b = _parse([{"objectID": "1", "title": "A", "url": "u"}, {"objectID": "9", "title": "B", "url": "u"}], NOW)
    assert a.point_id() == b.point_id()
