"""collectors.ossinsight._fetch_lang() のユニットテスト (httpx mock)"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.ossinsight import _fetch_lang

NOW = "2026-01-01T00:00:00+00:00"


def _mock_client(status_code: int = 200, json_body: dict | None = None):
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_body or {}
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=response,
        )
    else:
        response.raise_for_status.return_value = None
    client = MagicMock(spec=httpx.Client)
    client.get.return_value = response
    return client


def test_returns_repos_on_success():
    body = {
        "data": {
            "rows": [
                {"repo_name": "owner/repo", "stars": 500, "description": "desc", "primary_language": "Go"},
            ]
        }
    }
    client = _mock_client(200, body)
    repos = _fetch_lang(client, "Go", NOW)
    assert len(repos) == 1
    assert repos[0].full_name == "owner/repo"
    assert repos[0].stars == 500
    assert repos[0].lang == "Go"
    assert repos[0].source == "ossinsight"


def test_http_error_returns_empty():
    client = _mock_client(500)
    assert _fetch_lang(client, "Go", NOW) == []


def test_404_returns_empty():
    client = _mock_client(404)
    assert _fetch_lang(client, "Go", NOW) == []


def test_request_error_returns_empty():
    client = MagicMock(spec=httpx.Client)
    client.get.side_effect = httpx.RequestError("connection refused", request=MagicMock())
    assert _fetch_lang(client, "Go", NOW) == []


def test_skips_empty_repo_name():
    body = {"data": {"rows": [{"repo_name": "", "stars": 100}]}}
    client = _mock_client(200, body)
    assert _fetch_lang(client, "", NOW) == []


def test_stars_null_defaults_to_zero():
    body = {"data": {"rows": [{"repo_name": "owner/repo", "stars": None}]}}
    client = _mock_client(200, body)
    repos = _fetch_lang(client, "", NOW)
    assert repos[0].stars == 0


def test_stars_invalid_string_defaults_to_zero():
    body = {"data": {"rows": [{"repo_name": "owner/repo", "stars": "n/a"}]}}
    client = _mock_client(200, body)
    repos = _fetch_lang(client, "", NOW)
    assert repos[0].stars == 0


def test_empty_data_returns_empty():
    client = _mock_client(200, {})
    assert _fetch_lang(client, "Python", NOW) == []


def test_lang_filter_passed_to_request():
    client = _mock_client(200, {"data": {"rows": []}})
    _fetch_lang(client, "Rust", NOW)
    call_kwargs = client.get.call_args
    assert call_kwargs.kwargs["params"].get("language") == "Rust"


def test_no_lang_filter_when_empty():
    client = _mock_client(200, {"data": {"rows": []}})
    _fetch_lang(client, "", NOW)
    call_kwargs = client.get.call_args
    assert "language" not in call_kwargs.kwargs["params"]
