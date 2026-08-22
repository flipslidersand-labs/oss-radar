"""oss_radar.query — embed_query / SearchClient のユニットテスト"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from oss_radar.query import SearchClient, embed_query

FAKE_VEC = [0.1] * 768


def _mock_embed_response(vector: list[float] | None = None):
    response = MagicMock(spec=httpx.Response)
    response.raise_for_status.return_value = None
    response.json.return_value = {"vectors": [vector or FAKE_VEC]}
    return response


def _patch_httpx(response):
    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: mock_client
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = response
    return patch("oss_radar.query.httpx.Client", return_value=mock_client), mock_client


# ── embed_query ───────────────────────────────────────────────────────────────

def test_embed_query_returns_vector():
    patcher, mock_client = _patch_httpx(_mock_embed_response())
    with patcher:
        result = embed_query("search text", "http://embed/batch", "key", "sessions")
    assert result == FAKE_VEC


def test_embed_query_payload():
    patcher, mock_client = _patch_httpx(_mock_embed_response())
    with patcher:
        embed_query("hello", "http://embed/batch", "mykey", "sessions")
    payload = mock_client.post.call_args.kwargs["json"]
    assert payload["texts"] == ["hello"]
    assert payload["mode"] == "search"
    assert payload["collection"] == "sessions"


def test_embed_query_api_key_header():
    patcher, mock_client = _patch_httpx(_mock_embed_response())
    with patcher:
        embed_query("q", "http://embed/batch", "secret", "sessions")
    headers = mock_client.post.call_args.kwargs["headers"]
    assert headers["X-API-Key"] == "secret"


def test_embed_query_no_header_when_empty_key():
    patcher, mock_client = _patch_httpx(_mock_embed_response())
    with patcher:
        embed_query("q", "http://embed/batch", "", "sessions")
    headers = mock_client.post.call_args.kwargs["headers"]
    assert "X-API-Key" not in headers


def test_embed_query_propagates_http_error():
    response = MagicMock(spec=httpx.Response)
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401", request=MagicMock(), response=response
    )
    patcher, _ = _patch_httpx(response)
    with patcher, pytest.raises(httpx.HTTPStatusError):
        embed_query("q", "http://embed/batch")


# ── SearchClient ──────────────────────────────────────────────────────────────

def _make_client(qdrant_mock: MagicMock | None = None) -> tuple[SearchClient, MagicMock]:
    if qdrant_mock is None:
        qdrant_mock = MagicMock()
    with patch("oss_radar.query.QdrantClient", return_value=qdrant_mock):
        client = SearchClient("http://qdrant", "http://embed", "key", "sessions")
    return client, qdrant_mock


def test_search_calls_query_points():
    client, qdrant = _make_client()
    qdrant.query_points.return_value.points = []

    with patch.object(client, "_embed", return_value=FAKE_VEC):
        client.search("query text", "github-trending")

    qdrant.query_points.assert_called_once()
    kwargs = qdrant.query_points.call_args.kwargs
    assert kwargs["collection_name"] == "github-trending"
    assert kwargs["query"] == FAKE_VEC
    assert kwargs["limit"] == 10
    assert kwargs["with_payload"] is True


def test_search_passes_filters():
    client, qdrant = _make_client()
    qdrant.query_points.return_value.points = []

    with patch.object(client, "_embed", return_value=FAKE_VEC):
        client.search("q", "col", lang="Go", license_="MIT", stars_min=500)

    kwargs = qdrant.query_points.call_args.kwargs
    filt = kwargs["query_filter"]
    assert filt is not None
    keys = {c.key for c in filt.must}
    assert keys == {"lang", "license", "stars"}


def test_search_no_filter_when_defaults():
    client, qdrant = _make_client()
    qdrant.query_points.return_value.points = []

    with patch.object(client, "_embed", return_value=FAKE_VEC):
        client.search("q", "col")

    kwargs = qdrant.query_points.call_args.kwargs
    assert kwargs["query_filter"] is None


def test_search_returns_points():
    client, qdrant = _make_client()
    fake_point = MagicMock()
    fake_point.score = 0.95
    qdrant.query_points.return_value.points = [fake_point]

    with patch.object(client, "_embed", return_value=FAKE_VEC):
        results = client.search("q", "col")

    assert len(results) == 1
    assert results[0].score == 0.95


def test_search_custom_limit():
    client, qdrant = _make_client()
    qdrant.query_points.return_value.points = []

    with patch.object(client, "_embed", return_value=FAKE_VEC):
        client.search("q", "col", limit=25)

    assert qdrant.query_points.call_args.kwargs["limit"] == 25


def test_search_client_reuses_qdrant_instance():
    """同一 SearchClient は QdrantClient を使い回す（毎回生成しない）"""
    qdrant_mock = MagicMock()
    qdrant_mock.query_points.return_value.points = []
    client, _ = _make_client(qdrant_mock)

    with patch.object(client, "_embed", return_value=FAKE_VEC):
        client.search("q1", "col")
        client.search("q2", "col")

    assert qdrant_mock.query_points.call_count == 2
    assert client._qdrant is qdrant_mock


def test_search_client_has_persistent_http_client():
    """SearchClient が httpx.Client を _http として保持する"""
    client, _ = _make_client()
    assert hasattr(client, "_http")
    assert isinstance(client._http, httpx.Client)
