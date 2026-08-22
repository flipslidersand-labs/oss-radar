"""ingest.py のユニットテスト (httpx / QdrantClient mock)"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from ingest import BATCH_SIZE, _embed, _ensure_collection, ingest
from models import Repo


def _repo(name: str = "owner/repo") -> Repo:
    return Repo(
        full_name=name,
        description="desc",
        stars=100,
        lang="Go",
        topics=[],
        license="MIT",
        source="test",
        fetched_at="2026-01-01T00:00:00+00:00",
    )


def _fake_vectors(n: int) -> list[list[float]]:
    return [[0.1] * 768 for _ in range(n)]


# ── _embed ────────────────────────────────────────────────────────────────────

def test_embed_sends_correct_payload():
    fake_response = MagicMock()
    fake_response.json.return_value = {"vectors": _fake_vectors(2)}
    fake_response.raise_for_status.return_value = None

    with patch("ingest.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: mock_client
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = fake_response
        mock_client_cls.return_value = mock_client

        result = _embed(["text1", "text2"], "http://embed/batch", "key", "sessions")

    assert len(result) == 2
    payload = mock_client.post.call_args.kwargs["json"]
    assert payload["texts"] == ["text1", "text2"]
    assert payload["mode"] == "index"
    assert payload["collection"] == "sessions"


def test_embed_sets_api_key_header():
    fake_response = MagicMock()
    fake_response.json.return_value = {"vectors": _fake_vectors(1)}
    fake_response.raise_for_status.return_value = None

    with patch("ingest.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: mock_client
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = fake_response
        mock_client_cls.return_value = mock_client

        _embed(["t"], "http://embed/batch", "my-key")

    headers = mock_client.post.call_args.kwargs["headers"]
    assert headers["X-API-Key"] == "my-key"


def test_embed_omits_header_when_no_key():
    fake_response = MagicMock()
    fake_response.json.return_value = {"vectors": _fake_vectors(1)}
    fake_response.raise_for_status.return_value = None

    with patch("ingest.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: mock_client
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = fake_response
        mock_client_cls.return_value = mock_client

        _embed(["t"], "http://embed/batch", "")

    headers = mock_client.post.call_args.kwargs["headers"]
    assert "X-API-Key" not in headers


# ── _ensure_collection ────────────────────────────────────────────────────────

def test_ensure_collection_creates_when_missing():
    qdrant = MagicMock()
    col = MagicMock()
    col.name = "other-collection"
    qdrant.get_collections.return_value.collections = [col]

    _ensure_collection(qdrant, "github-trending")

    qdrant.create_collection.assert_called_once()
    kwargs = qdrant.create_collection.call_args.kwargs
    assert kwargs["collection_name"] == "github-trending"


def test_ensure_collection_skips_when_exists():
    qdrant = MagicMock()
    col = MagicMock()
    col.name = "github-trending"
    qdrant.get_collections.return_value.collections = [col]

    _ensure_collection(qdrant, "github-trending")

    qdrant.create_collection.assert_not_called()


# ── ingest ────────────────────────────────────────────────────────────────────

def test_ingest_empty_returns_zero():
    assert ingest([], "http://qdrant", "http://embed", "col") == 0


def test_ingest_single_batch():
    repos = [_repo(f"owner/repo-{i}") for i in range(3)]
    vectors = _fake_vectors(3)

    with patch("ingest.QdrantClient") as mock_qdrant_cls, \
         patch("ingest._embed", return_value=vectors):
        mock_qdrant = MagicMock()
        col = MagicMock()
        col.name = "col"
        mock_qdrant.get_collections.return_value.collections = [col]
        mock_qdrant_cls.return_value = mock_qdrant

        count = ingest(repos, "http://qdrant", "http://embed", "col")

    assert count == 3
    mock_qdrant.upsert.assert_called_once()


def test_ingest_embed_mismatch_raises():
    repos = [_repo(f"owner/r{i}") for i in range(3)]

    with patch("ingest.QdrantClient") as mock_qdrant_cls, \
         patch("ingest._embed", return_value=_fake_vectors(2)):  # 3件送って2件返る
        mock_qdrant = MagicMock()
        col = MagicMock()
        col.name = "col"
        mock_qdrant.get_collections.return_value.collections = [col]
        mock_qdrant_cls.return_value = mock_qdrant

        with pytest.raises(ValueError, match="embed mismatch"):
            ingest(repos, "http://qdrant", "http://embed", "col")


def test_ingest_multi_batch():
    n = BATCH_SIZE + 10  # 74件 → 2バッチ
    repos = [_repo(f"owner/r{i}") for i in range(n)]

    call_count = 0
    def fake_embed(texts, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        return _fake_vectors(len(texts))

    with patch("ingest.QdrantClient") as mock_qdrant_cls, \
         patch("ingest._embed", side_effect=fake_embed):
        mock_qdrant = MagicMock()
        col = MagicMock()
        col.name = "col"
        mock_qdrant.get_collections.return_value.collections = [col]
        mock_qdrant_cls.return_value = mock_qdrant

        count = ingest(repos, "http://qdrant", "http://embed", "col")

    assert count == n
    assert call_count == 2  # BATCH_SIZE=64 → batch0=64, batch1=10
    assert mock_qdrant.upsert.call_count == 2


def test_ingest_exact_batch_size():
    repos = [_repo(f"owner/r{i}") for i in range(BATCH_SIZE)]

    with patch("ingest.QdrantClient") as mock_qdrant_cls, \
         patch("ingest._embed", return_value=_fake_vectors(BATCH_SIZE)):
        mock_qdrant = MagicMock()
        col = MagicMock()
        col.name = "col"
        mock_qdrant.get_collections.return_value.collections = [col]
        mock_qdrant_cls.return_value = mock_qdrant

        count = ingest(repos, "http://qdrant", "http://embed", "col")

    assert count == BATCH_SIZE
    mock_qdrant.upsert.assert_called_once()


def test_ingest_point_id_deterministic():
    """同じ full_name は常に同じ point_id になる"""
    r = _repo("owner/stable")
    assert r.point_id() == r.point_id()


def test_ingest_uses_collection_name():
    repos = [_repo()]

    with patch("ingest.QdrantClient") as mock_qdrant_cls, \
         patch("ingest._embed", return_value=_fake_vectors(1)):
        mock_qdrant = MagicMock()
        col = MagicMock()
        col.name = "other"
        mock_qdrant.get_collections.return_value.collections = [col]
        mock_qdrant_cls.return_value = mock_qdrant

        ingest(repos, "http://qdrant", "http://embed", "my-collection")

    upsert_call = mock_qdrant.upsert.call_args
    assert upsert_call.kwargs["collection_name"] == "my-collection"
