#!/usr/bin/env python3
"""セマンティック検索 CLI

Usage:
    python search.py "ストリーム処理の設計参考になるOSS"
    python search.py "組み込みやすいGoライブラリ" --lang Go --limit 10
    python search.py "MLパイプライン" --license MIT --stars-min 500
    python search.py "stream processing" --source ossinsight
    python search.py "Go framework" --since 2026-08-20
"""
import os

import click
from dotenv import load_dotenv

from oss_radar.query import SearchClient

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
EMBED_URL = os.getenv("EMBED_URL", "http://192.168.68.63:9092/embed/batch")
EMBED_API_KEY = os.getenv("EMBED_API_KEY", "")
EMBED_COLLECTION = os.getenv("EMBED_COLLECTION", "sessions")
COLLECTION = os.getenv("COLLECTION", "github-trending")


@click.command()
@click.argument("query")
@click.option("--lang", default=None, help="言語フィルタ (例: Go, Python, Rust)")
@click.option("--license", "license_", default=None, help="ライセンスフィルタ (例: MIT, Apache-2.0)")
@click.option("--stars-min", default=0, type=int, help="最低スター数")
@click.option("--source", default=None, help="収集元フィルタ (例: ossinsight, github-trending)")
@click.option("--since", default=None, help="収集日時フィルタ YYYY-MM-DD (fetched_at >= since)")
@click.option("--limit", default=10, type=int, help="表示件数")
def search(query: str, lang: str | None, license_: str | None, stars_min: int,
           source: str | None, since: str | None, limit: int):
    client = SearchClient(QDRANT_URL, EMBED_URL, EMBED_API_KEY, EMBED_COLLECTION)
    results = client.search(query, COLLECTION, lang=lang, license_=license_,
                            stars_min=stars_min, source=source, since=since, limit=limit)

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
