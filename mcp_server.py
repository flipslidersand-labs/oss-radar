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

import httpx
from dotenv import load_dotenv
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue, Range

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
EMBED_URL = os.getenv("EMBED_URL", "http://192.168.68.63:9092/embed/batch")
EMBED_API_KEY = os.getenv("EMBED_API_KEY", "")
EMBED_COLLECTION = os.getenv("EMBED_COLLECTION", "sessions")
COLLECTION = os.getenv("COLLECTION", "github-trending")


def _embed(text: str) -> list[float]:
    headers = {"X-API-Key": EMBED_API_KEY} if EMBED_API_KEY else {}
    with httpx.Client(timeout=60.0) as client:
        r = client.post(
            EMBED_URL,
            json={"texts": [text], "collection": EMBED_COLLECTION, "mode": "search"},
            headers=headers,
        )
        r.raise_for_status()
    return r.json()["vectors"][0]


def _build_filter(lang: str | None, license_: str | None, stars_min: int) -> Filter | None:
    conditions = []
    if lang:
        conditions.append(FieldCondition(key="lang", match=MatchValue(value=lang)))
    if license_:
        conditions.append(FieldCondition(key="license", match=MatchValue(value=license_)))
    if stars_min > 0:
        conditions.append(FieldCondition(key="stars", range=Range(gte=stars_min)))
    return Filter(must=conditions) if conditions else None


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
    limit: int = min(int(args.get("limit", 10)), 50)

    if not query:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="query は必須です")],
            isError=True,
        )

    try:
        vec = _embed(query)
        client = QdrantClient(url=QDRANT_URL)
        filt = _build_filter(lang, license_, stars_min)
        results = client.query_points(
            collection_name=COLLECTION,
            query=vec,
            query_filter=filt,
            limit=limit,
            with_payload=True,
        ).points
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


async def main() -> None:
    server = Server("oss-radar", on_list_tools=on_list_tools, on_call_tool=on_call_tool)
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
