"""mcp_server: on_list_tools のスキーマと on_call_tool の各分岐"""
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import mcp_server


def _call(arguments, name="search_trending", client=None):
    params = SimpleNamespace(name=name, arguments=arguments)
    with patch.object(mcp_server, "_get_client", return_value=client or MagicMock()):
        r = asyncio.run(mcp_server.on_call_tool(None, params))
    return r.model_dump(by_alias=True)


def _client(results=None, exc=None):
    c = MagicMock()
    if exc:
        c.search.side_effect = exc
    else:
        c.search.return_value = results or []
    return c


def _hit(score=0.5, payload=None):
    return SimpleNamespace(score=score, payload=payload)


def _text(r):
    return r["content"][0]["text"]


def test_list_tools_schema():
    r = asyncio.run(mcp_server.on_list_tools(None, None)).model_dump(by_alias=True)
    (tool,) = r["tools"]
    assert tool["name"] == "search_trending"
    assert tool["inputSchema"]["required"] == ["query"]
    assert {"lang", "license", "stars_min", "source", "since", "limit"} <= set(tool["inputSchema"]["properties"])


def test_unknown_tool_is_error():
    r = _call({"query": "x"}, name="nope")
    assert r["isError"] is True
    assert "Unknown tool: nope" in _text(r)


def test_empty_query_is_error():
    c = _client()
    r = _call({"query": ""}, client=c)
    assert r["isError"] is True
    assert "query は必須" in _text(r)
    c.search.assert_not_called()


def test_missing_arguments_is_error():
    assert _call(None)["isError"] is True


def test_search_exception_is_error():
    r = _call({"query": "x"}, client=_client(exc=RuntimeError("boom")))
    assert r["isError"] is True
    assert "検索エラー: boom" in _text(r)


def test_no_results_is_not_error():
    r = _call({"query": "x"}, client=_client([]))
    assert r["isError"] is False
    assert "結果なし" in _text(r)


def test_limit_clamped_to_50():
    c = _client([])
    _call({"query": "x", "limit": 999}, client=c)
    assert c.search.call_args.kwargs["limit"] == 50


def test_filters_forwarded():
    c = _client([])
    args = {"query": "x", "lang": "Go", "license": "MIT", "stars_min": 10, "source": "s", "since": "2026-01-01"}
    _call(args, client=c)
    kw = c.search.call_args.kwargs
    got = (kw["lang"], kw["license_"], kw["stars_min"], kw["source"], kw["since"])
    assert got == ("Go", "MIT", 10, "s", "2026-01-01")


def test_payload_none_fields_become_defaults():
    r = _call({"query": "x"}, client=_client([_hit(0.123456, {"full_name": "o/r", "lang": None, "license": None,
                                                            "description": None, "topics": None, "source": None})]))
    (row,) = json.loads(_text(r))
    assert r["isError"] is False
    assert row == {"score": 0.1235, "full_name": "o/r", "stars": 0, "lang": "", "license": "",
                   "description": "", "topics": [], "source": ""}


def test_payload_none_whole_does_not_crash():
    r = _call({"query": "x"}, client=_client([_hit(0.5, None)]))
    (row,) = json.loads(_text(r))
    assert row["full_name"] == "" and row["stars"] == 0
