"""community.dedup() と Post.to_payload() のテスト"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from community import dedup
from models import Post


def _p(url, score, source="hn"):
    return Post(url=url, title="t", score=score, source=source, fetched_at="x")


def test_dedup_keeps_highest_score_per_url():
    out = dedup([_p("u", 1), _p("u", 9, "hatena"), _p("v", 2), _p("", 5)])
    assert {(p.url, p.score, p.source) for p in out} == {("u", 9, "hatena"), ("v", 2, "hn")}


def test_payload_has_search_compat_keys():
    d = _p("https://a", 7).to_payload()
    assert d["full_name"] == "t" and d["stars"] == 7 and d["description"] == "https://a"
