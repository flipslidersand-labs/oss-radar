"""collectors.bestofjs — レスポンス欠落キーへの耐性"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "collectors"))

from bestofjs import _fetch_lang, collect


def _resp(body: dict):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = body
    return r


def test_fetch_lang_skips_items_missing_full_name_and_defaults_stars():
    body = {
        "items": [
            {"stargazers_count": 10},  # full_name 欠落 → スキップ
            {"full_name": "org/ok"},  # stargazers_count 欠落 → 0
            {"full_name": "org/full", "stargazers_count": 99},
        ]
    }
    with patch("bestofjs.httpx.get", return_value=_resp(body)):
        repos = _fetch_lang("JavaScript", {}, "2026-10-01", 50, "now")
    assert [(r.full_name, r.stars) for r in repos] == [("org/ok", 0), ("org/full", 99)]


def _err(status: int, headers: dict | None = None):
    resp = MagicMock()
    resp.status_code = status
    resp.headers = headers or {}
    r = MagicMock()
    r.raise_for_status.side_effect = httpx.HTTPStatusError(f"HTTP {status}", request=MagicMock(), response=resp)
    return r


def _fetch(side_effect):
    with patch("bestofjs.httpx.get", side_effect=side_effect) as get, patch("bestofjs.time.sleep") as sleep:
        repos = _fetch_lang("JavaScript", {}, "2026-10-01", 50, "now")
    return repos, get, sleep


def test_429_then_success_retries_after_retry_after():
    ok = _resp({"items": [{"full_name": "o/r", "stargazers_count": 5}]})
    repos, get, sleep = _fetch([_err(429, {"Retry-After": "7"}), ok])
    assert [r.full_name for r in repos] == ["o/r"]
    assert get.call_count == 2
    sleep.assert_called_once_with(7)


def test_429_without_retry_after_defaults_to_60s():
    _, _, sleep = _fetch([_err(429), _resp({"items": []})])
    sleep.assert_called_once_with(60)


def test_429_then_http_error_returns_empty():
    repos, get, _ = _fetch([_err(429, {"Retry-After": "1"}), _err(503)])
    assert repos == []
    assert get.call_count == 2


def test_429_then_request_error_returns_empty():
    repos, _, _ = _fetch([_err(429, {"Retry-After": "1"}), httpx.ConnectError("down")])
    assert repos == []


def test_non_429_http_error_returns_empty_without_retry():
    repos, get, sleep = _fetch([_err(500)])
    assert repos == []
    assert get.call_count == 1
    sleep.assert_not_called()


def test_request_error_returns_empty():
    repos, _, _ = _fetch([httpx.ConnectError("down")])
    assert repos == []


def test_license_and_topics_defaults():
    body = {"items": [{"full_name": "o/r", "license": None, "topics": None}]}
    repos, _, _ = _fetch([_resp(body)])
    assert repos[0].license is None
    assert repos[0].topics == []


def test_collect_combines_javascript_and_typescript():
    def fake_get(url, params, **kw):
        lang = params["q"].split()[0].split(":")[1]
        return _resp({"items": [{"full_name": f"o/{lang}", "stargazers_count": 1}]})

    with patch("bestofjs.httpx.get", side_effect=fake_get):
        repos = collect()
    assert [r.full_name for r in repos] == ["o/JavaScript", "o/TypeScript"]
