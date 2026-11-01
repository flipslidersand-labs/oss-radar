#!/usr/bin/env python3
"""技術者コミュニティ(HN/Zenn/はてブ)収集 + ingest

Usage:
    python community.py --dry-run     # 取得と件数表示のみ、Qdrant には書かない
    python community.py               # community-posts コレクションへ ingest
検索: COLLECTION=community-posts python search.py "クエリ"
"""

import os
import time

import click
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
EMBED_URL = os.getenv("EMBED_URL", "http://localhost:9092/embed/batch")
EMBED_API_KEY = os.getenv("EMBED_API_KEY", "")
EMBED_COLLECTION = os.getenv("EMBED_COLLECTION", "sessions")
COMMUNITY_COLLECTION = os.getenv("COMMUNITY_COLLECTION", "community-posts")


def dedup(posts) -> list:
    """url 単位で重複排除。同一 url は score が高い方を残す。"""
    best: dict[str, object] = {}
    for p in posts:
        if p.url and (p.url not in best or p.score > best[p.url].score):
            best[p.url] = p
    return list(best.values())


@click.command()
@click.option("--dry-run", is_flag=True, default=False, help="Qdrant に書かず結果だけ表示")
def main(dry_run: bool):
    from collectors import hatena, hn, zenn

    all_posts = []
    for name, mod in (("hn", hn), ("zenn", zenn), ("hatena", hatena)):
        t0 = time.monotonic()
        try:
            posts = mod.collect()
        except Exception as e:  # noqa: BLE001  1 ソースの失敗で全体を止めない
            click.echo(f"  ✗ {name}: {e}", err=True)
            continue
        click.echo(f"{name}: {len(posts)} posts ({time.monotonic() - t0:.1f}s)")
        all_posts.extend(posts)

    deduped = dedup(all_posts)
    click.echo(f"合計: {len(all_posts)} → dedup後: {len(deduped)}")

    if dry_run:
        click.echo("[dry-run] Qdrant への書き込みをスキップ")
        for p in sorted(deduped, key=lambda x: -x.score)[:10]:
            click.echo(f"  {p.score:>5}  [{p.source}] {p.title[:70]}")
        return

    from ingest import ingest

    count = ingest(
        deduped, QDRANT_URL, EMBED_URL, COMMUNITY_COLLECTION, EMBED_API_KEY, EMBED_COLLECTION, QDRANT_API_KEY
    )
    click.echo(f"完了: {count} points upserted → {COMMUNITY_COLLECTION}")


if __name__ == "__main__":
    main()
