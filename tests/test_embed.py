"""oss_radar.embed.post_embed"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from oss_radar.embed import post_embed


def _http(vectors=None, error=None):
    http = MagicMock()
    resp = MagicMock()
    if error:
        resp.raise_for_status.side_effect = error
    resp.json.return_value = {"vectors": vectors or [[0.1]]}
    http.post.return_value = resp
    return http


def test_payload_includes_mode_and_collection():
    http = _http()
    post_embed(http, "http://e", ["a", "b"], "sessions", "index")
    assert http.post.call_args.args == ("http://e",)
    assert http.post.call_args.kwargs["json"] == {"texts": ["a", "b"], "collection": "sessions", "mode": "index"}


def test_api_key_header_only_when_set():
    http = _http()
    post_embed(http, "http://e", ["a"], "c", "search", "secret")
    assert http.post.call_args.kwargs["headers"] == {"X-API-Key": "secret"}
    post_embed(http, "http://e", ["a"], "c", "search", "")
    assert http.post.call_args.kwargs["headers"] == {}


def test_returns_vectors():
    assert post_embed(_http([[1.0], [2.0]]), "http://e", ["a", "b"], "c", "index") == [[1.0], [2.0]]


def test_http_error_propagates():
    err = httpx.HTTPStatusError("401", request=MagicMock(), response=MagicMock())
    with pytest.raises(httpx.HTTPStatusError):
        post_embed(_http(error=err), "http://e", ["a"], "c", "index")
