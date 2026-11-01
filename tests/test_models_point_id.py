"""Repo / Post の point_id は既存 Qdrant コレクションの ID と一致し続ける(変更禁止の固定値)"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Post, Repo


def test_repo_point_id_is_pinned():
    r = Repo("org/repo", "", 1, None, [], None, "github_search", "t")
    assert r.point_id() == "ab689d8c-0ded-93c4-deac-5900b7950690"


def test_post_point_id_is_pinned():
    p = Post("https://x.dev/a", "t", 1, "hn", "t")
    assert p.point_id() == "5ef27561-6117-4ffb-b145-58f2a19ed010"
