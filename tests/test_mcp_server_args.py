"""mcp_server.on_call_tool の引数検証(#93): 非数値の stars_min/limit は例外でなく isError を返す"""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

import mcp_server


def _call(arguments):
    params = SimpleNamespace(name="search_trending", arguments=arguments)
    r = asyncio.run(mcp_server.on_call_tool(None, params))
    return r.model_dump(by_alias=True)  # mcp のバージョンで属性名が isError/is_error と変わるため別名で比較


def test_non_numeric_stars_min_returns_error():
    r = _call({"query": "x", "stars_min": "abc"})
    assert r["isError"] is True
    assert "整数" in r["content"][0]["text"]


def test_non_numeric_limit_returns_error():
    r = _call({"query": "x", "limit": None})
    assert r["isError"] is True
