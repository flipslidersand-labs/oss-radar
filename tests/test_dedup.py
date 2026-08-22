"""main.dedup() のユニットテスト"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import dedup
from models import Repo


def _repo(full_name: str, stars: int = 0) -> Repo:
    return Repo(
        full_name=full_name,
        description="",
        stars=stars,
        lang=None,
        topics=[],
        license=None,
        source="test",
        fetched_at="2026-01-01T00:00:00+00:00",
    )


def test_dedup_removes_duplicates():
    repos = [_repo("owner/a"), _repo("owner/b"), _repo("owner/a")]
    result = dedup(repos)
    assert len(result) == 2
    assert result[0].full_name == "owner/a"
    assert result[1].full_name == "owner/b"


def test_dedup_preserves_order():
    repos = [_repo("z/z"), _repo("a/a"), _repo("m/m")]
    result = dedup(repos)
    assert [r.full_name for r in result] == ["z/z", "a/a", "m/m"]


def test_dedup_filters_empty_full_name():
    repos = [_repo(""), _repo("owner/a"), _repo("")]
    result = dedup(repos)
    assert len(result) == 1
    assert result[0].full_name == "owner/a"


def test_dedup_empty_list():
    assert dedup([]) == []


def test_dedup_all_duplicates():
    repos = [_repo("owner/a")] * 5
    result = dedup(repos)
    assert len(result) == 1


def test_dedup_keeps_first_occurrence():
    repos = [_repo("owner/a", stars=100), _repo("owner/a", stars=999)]
    result = dedup(repos)
    assert len(result) == 1
    assert result[0].stars == 100
