#!/usr/bin/env python3
"""セマンティック検索 CLI

Usage:
    python search.py "ストリーム処理の設計参考になるOSS"
    python search.py "組み込みやすいGoライブラリ" --lang Go --limit 10
    python search.py "MLパイプライン" --license MIT --stars-min 500
"""
import os
import sys
import click
import httpx
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range, Query

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
EMBED_URL = os.getenv("EMBED_URL", "http://192.168.68.63:9092/embed/batch")
EMBED_API_KEY = os.getenv("EMBED_API_KEY", "")
EMBED_COLLECTION = os.getenv("EMBED_COLLECTION", "sessions")
COLLECTION = os.getenv("COLLECTION", "github-trending")


def _embed_query(text: str) -> list[float]:
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


@click.command()
@click.argument("query")
@click.option("--lang", default=None, help="言語フィルタ (例: Go, Python, Rust)")
@click.option("--license", "license_", default=None, help="ライセンスフィルタ (例: MIT, Apache-2.0)")
@click.option("--stars-min", default=0, type=int, help="最低スター数")
@click.option("--limit", default=10, type=int, help="表示件数")
def search(query: str, lang: str | None, license_: str | None, stars_min: int, limit: int):
    vec = _embed_query(query)
    client = QdrantClient(url=QDRANT_URL)
    filt = _build_filter(lang, license_, stars_min)

    results = client.query_points(
        collection_name=COLLECTION,
        query=vec,
        query_filter=filt,
        limit=limit,
        with_payload=True,
    ).points

    if not results:
        click.echo("結果なし。まず `python main.py` で収集してください。")
        return

    click.echo(f"\n{'Score':>6}  {'Stars':>6}  {'Lang':<12}  {'Repo':<40}  Description")
    click.echo("-" * 100)
    for r in results:
        p = r.payload
        desc = (p.get("description") or "")[:60]
        click.echo(
            f"{r.score:>6.3f}  {p.get('stars', 0):>6}  {(p.get('lang') or '-'):<12}"
            f"  {p.get('full_name', ''):<40}  {desc}"
        )


if __name__ == "__main__":
    search()
