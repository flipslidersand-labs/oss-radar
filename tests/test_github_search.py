"""collectors.github_search — rate limit / retry ハンドリングのユニットテスト"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "collectors"))

from github_search import _get_page, collect

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_response(status: int, body: dict | None = None, headers: dict | None = None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.headers = headers or {}
    if status >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status}", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
        resp.json.return_value = body or {}
    return resp


def _mock_client(*responses):
    client = MagicMock(spec=httpx.Client)
    client.get.side_effect = responses
    return client


# ── _get_page ─────────────────────────────────────────────────────────────────

def test_get_page_success():
    payload = {"items": [{"full_name": "org/repo"}]}
    client = _mock_client(_make_response(200, payload))
    result = _get_page(client, {}, {})
    assert result == payload


def test_get_page_429_returns_empty(capsys):
    resp = _make_response(429, headers={"X-RateLimit-Reset": "1700000000"})
    client = _mock_client(resp)
    result = _get_page(client, {}, {})
    assert result == {}
    captured = capsys.readouterr()
    assert "rate limited" in captured.err
    assert "429" in captured.err
    assert "1700000000" in captured.err


def test_get_page_403_returns_empty(capsys):
    resp = _make_response(403, headers={})
    client = _mock_client(resp)
    result = _get_page(client, {}, {})
    assert result == {}
    captured = capsys.readouterr()
    assert "rate limited" in captured.err
    assert "403" in captured.err


def test_get_page_429_no_reset_header(capsys):
    resp = _make_response(429, headers={})
    client = _mock_client(resp)
    result = _get_page(client, {}, {})
    assert result == {}
    captured = capsys.readouterr()
    assert "unknown" in captured.err


def test_get_page_5xx_retries_then_succeeds(capsys):
    payload = {"items": []}
    client = _mock_client(
        _make_response(503),
        _make_response(200, payload),
    )
    with patch("github_search.time.sleep") as mock_sleep:
        result = _get_page(client, {}, {})
    assert result == payload
    mock_sleep.assert_called_once_with(1)
    captured = capsys.readouterr()
    assert "retry 1/2" in captured.err


def test_get_page_5xx_exhausts_retries():
    client = _mock_client(
        _make_response(500),
        _make_response(502),
        _make_response(503),
    )
    with patch("github_search.time.sleep"):
        with pytest.raises(httpx.HTTPStatusError):
            _get_page(client, {}, {})
    assert client.get.call_count == 3


def test_get_page_5xx_backoff_waits(capsys):
    payload = {"items": []}
    client = _mock_client(
        _make_response(500),
        _make_response(500),
        _make_response(200, payload),
    )
    with patch("github_search.time.sleep") as mock_sleep:
        result = _get_page(client, {}, {})
    assert result == payload
    assert mock_sleep.call_args_list == [call(1), call(2)]


def test_get_page_non_rate_limit_4xx_raises():
    client = _mock_client(_make_response(401))
    with pytest.raises(httpx.HTTPStatusError):
        _get_page(client, {}, {})


# ── collect (integration) ─────────────────────────────────────────────────────

_ITEM = {
    "full_name": "org/repo",
    "description": "desc",
    "stargazers_count": 100,
    "language": "Go",
    "topics": ["go"],
    "license": {"spdx_id": "MIT"},
}


def test_collect_returns_repos():
    page_data = {"items": [_ITEM]}
    with patch("github_search._get_page", return_value=page_data):
        repos = collect("token", days_back=7, pages=1)
    assert len(repos) == 1
    assert repos[0].full_name == "org/repo"
    assert repos[0].source == "github_search"


def test_collect_rate_limit_skips_page():
    with patch("github_search._get_page", return_value={}):
        repos = collect("token", days_back=7, pages=2)
    assert repos == []


def test_collect_partial_pages():
    responses = [{"items": [_ITEM]}, {}]
    with patch("github_search._get_page", side_effect=responses):
        repos = collect("token", days_back=7, pages=2)
    assert len(repos) == 1
