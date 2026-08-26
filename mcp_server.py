#!/usr/bin/env python3
"""oss-radar MCP サーバー

Claude Code から直接 github-trending コレクションをセマンティック検索する。

起動:
    python mcp_server.py

.claude/settings.json への登録例:
    "mcpServers": {
        "oss-radar": {
            "command": "python",
            "args": ["/path/to/oss-radar/mcp_server.py"],
            "env": {
                "QDRANT_URL": "http://localhost:6333",
                "EMBED_URL": "http://192.168.68.63:9092/embed/batch",
                "EMBED_API_KEY": "xxxx",
                "EMBED_COLLECTION": "sessions",
                "COLLECTION": "github-trending"
            }
        }
    }
"""
import asyncio
import json
import os

from dotenv import load_dotenv
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from oss_radar.query import SearchClient

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
EMBED_URL = os.getenv("EMBED_URL", "http://192.168.68.63:9092/embed/batch")
EMBED_API_KEY = os.getenv("EMBED_API_KEY", "")
EMBED_COLLECTION = os.getenv("EMBED_COLLECTION", "sessions")
COLLECTION = os.getenv("COLLECTION", "github-trending")

_search_client: SearchClient | None = None


def _get_client() -> SearchClient:
    global _search_client
    if _search_client is None:
        _search_client = SearchClient(QDRANT_URL, EMBED_URL, EMBED_API_KEY, EMBED_COLLECTION)
    return _search_client


SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "自然言語の検索クエリ（例: 'ストリーム処理の設計参考になるOSS'）",
        },
        "lang": {
            "type": "string",
            "description": "言語フィルタ（例: Go, Python, Rust）。省略時はフィルタなし",
        },
        "license": {
            "type": "string",
            "description": "ライセンスフィルタ（例: MIT, Apache-2.0）。省略時はフィルタなし",
        },
        "stars_min": {
            "type": "integer",
            "description": "最低スター数（デフォルト: 0）",
            "default": 0,
        },
        "source": {
            "type": "string",
            "description": "収集元フィルタ（例: ossinsight, github-trending）。省略時はフィルタなし",
        },
        "since": {
            "type": "string",
            "description": "収集日時フィルタ YYYY-MM-DD。fetched_at がこの日時以降のものに絞る。省略時はフィルタなし",
        },
        "limit": {
            "type": "integer",
            "description": "返却件数（デフォルト: 10、最大: 50）",
            "default": 10,
        },
    },
    "required": ["query"],
}


async def on_list_tools(ctx, params) -> types.ListToolsResult:
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name="search_trending",
                description=(
                    "github-trending Qdrant コレクションをセマンティック検索する。"
                    "収集済みのGitHubトレンドOSSを自然言語で検索できる。"
                ),
                inputSchema=SEARCH_SCHEMA,
            )
        ]
    )


async def on_call_tool(ctx, params) -> types.CallToolResult:
    if params.name != "search_trending":
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Unknown tool: {params.name}")],
            isError=True,
        )

    args = params.arguments or {}
    query: str = args.get("query", "")
    lang: str | None = args.get("lang")
    license_: str | None = args.get("license")
    stars_min: int = int(args.get("stars_min", 0))
    source: str | None = args.get("source")
    since: str | None = args.get("since")
    limit: int = min(int(args.get("limit", 10)), 50)

    if not query:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="query は必須です")],
            isError=True,
        )

    try:
        results = _get_client().search(
            query, COLLECTION, lang=lang, license_=license_,
            stars_min=stars_min, source=source, since=since, limit=limit,
        )
    except Exception as e:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"検索エラー: {e}")],
            isError=True,
        )

    if not results:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="結果なし。まず `python main.py` で収集してください。")],
            isError=False,
        )

    rows = []
    for r in results:
        p = r.payload or {}
        rows.append({
            "score": round(r.score, 4),
            "full_name": p.get("full_name", ""),
            "stars": p.get("stars", 0),
            "lang": p.get("lang") or "",
            "license": p.get("license") or "",
            "description": p.get("description") or "",
            "topics": p.get("topics") or [],
            "source": p.get("source") or "",
        })

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(rows, ensure_ascii=False, indent=2))],
        isError=False,
    )


def _check_env() -> None:
    import sys
    warnings = []
    if not EMBED_API_KEY:
        warnings.append("EMBED_API_KEY が未設定です。embedding-svc の認証に失敗します")
    if "192.168.68" in EMBED_URL and not os.getenv("EMBED_URL"):
        warnings.append(f"EMBED_URL がデフォルト値 ({EMBED_URL}) のままです")
    for w in warnings:
        print(f"[oss-radar MCP WARN] {w}", file=sys.stderr)


async def main() -> None:
    _check_env()
    server = Server("oss-radar", on_list_tools=on_list_tools, on_call_tool=on_call_tool)
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
