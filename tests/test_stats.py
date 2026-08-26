"""oss_radar/stats.py のユニットテスト"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from oss_radar.stats import (
    STATS_COLLECTION,
    _ensure_stats_collection,
    _make_point_id,
    record_snapshot,
)

# ── _make_point_id ────────────────────────────────────────────────────────────

def test_make_point_id_deterministic():
    """同じ (date, source) は常に同じ ID を返す"""
    pid = _make_point_id("2026-08-26", "github_search")
    assert pid == _make_point_id("2026-08-26", "github_search")


def test_make_point_id_different_sources():
    """ソースが異なれば ID が変わる"""
    pid1 = _make_point_id("2026-08-26", "github_search")
    pid2 = _make_point_id("2026-08-26", "gh_trending")
    assert pid1 != pid2


def test_make_point_id_different_dates():
    """日付が異なれば ID が変わる"""
    pid1 = _make_point_id("2026-08-25", "github_search")
    pid2 = _make_point_id("2026-08-26", "github_search")
    assert pid1 != pid2


def test_make_point_id_is_int():
    """返り値は整数"""
    pid = _make_point_id("2026-08-26", "ossinsight")
    assert isinstance(pid, int)


# ── _ensure_stats_collection ──────────────────────────────────────────────────

def test_ensure_stats_collection_creates_when_missing():
    client = MagicMock()
    col = MagicMock()
    col.name = "other"
    client.get_collections.return_value.collections = [col]

    _ensure_stats_collection(client)

    client.create_collection.assert_called_once()
    kwargs = client.create_collection.call_args.kwargs
    assert kwargs["collection_name"] == STATS_COLLECTION


def test_ensure_stats_collection_skips_when_exists():
    client = MagicMock()
    col = MagicMock()
    col.name = STATS_COLLECTION
    client.get_collections.return_value.collections = [col]

    _ensure_stats_collection(client)

    client.create_collection.assert_not_called()


# ── record_snapshot ───────────────────────────────────────────────────────────

def test_record_snapshot_upserts_correct_payload():
    with patch("oss_radar.stats.QdrantClient") as mock_qdrant_cls, \
         patch("oss_radar.stats.date") as mock_date:
        mock_date.today.return_value.isoformat.return_value = "2026-08-26"

        mock_qdrant = MagicMock()
        col = MagicMock()
        col.name = STATS_COLLECTION
        mock_qdrant.get_collections.return_value.collections = [col]
        mock_qdrant_cls.return_value = mock_qdrant

        record_snapshot("http://qdrant:6333", "github_search", 42, 3.14)

    mock_qdrant.upsert.assert_called_once()
    upsert_kwargs = mock_qdrant.upsert.call_args.kwargs
    assert upsert_kwargs["collection_name"] == STATS_COLLECTION
    points = upsert_kwargs["points"]
    assert len(points) == 1
    payload = points[0].payload
    assert payload["date"] == "2026-08-26"
    assert payload["source"] == "github_search"
    assert payload["count"] == 42
    assert payload["elapsed_sec"] == 3.14


def test_record_snapshot_vector_is_dummy():
    with patch("oss_radar.stats.QdrantClient") as mock_qdrant_cls, \
         patch("oss_radar.stats.date") as mock_date:
        mock_date.today.return_value.isoformat.return_value = "2026-08-26"

        mock_qdrant = MagicMock()
        col = MagicMock()
        col.name = STATS_COLLECTION
        mock_qdrant.get_collections.return_value.collections = [col]
        mock_qdrant_cls.return_value = mock_qdrant

        record_snapshot("http://qdrant:6333", "ossinsight", 10, 1.0)

    points = mock_qdrant.upsert.call_args.kwargs["points"]
    assert points[0].vector == [0.0]


def test_record_snapshot_point_id_matches_helper():
    with patch("oss_radar.stats.QdrantClient") as mock_qdrant_cls, \
         patch("oss_radar.stats.date") as mock_date:
        mock_date.today.return_value.isoformat.return_value = "2026-08-26"

        mock_qdrant = MagicMock()
        col = MagicMock()
        col.name = STATS_COLLECTION
        mock_qdrant.get_collections.return_value.collections = [col]
        mock_qdrant_cls.return_value = mock_qdrant

        record_snapshot("http://qdrant:6333", "bestofjs", 5, 0.5)

    points = mock_qdrant.upsert.call_args.kwargs["points"]
    expected_id = _make_point_id("2026-08-26", "bestofjs")
    assert points[0].id == expected_id
