#!/usr/bin/env python3
"""収集 + ingest オーケストレーション

Usage:
    python main.py                    # 全ソース収集
    python main.py --skip-ossinsight  # ossinsight をスキップ
    python main.py --dry-run          # dedup 結果だけ表示、Qdrant には書かない
"""
import os

import click
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
EMBED_URL = os.getenv("EMBED_URL", "http://192.168.68.63:9092/embed/batch")
EMBED_API_KEY = os.getenv("EMBED_API_KEY", "")
EMBED_COLLECTION = os.getenv("EMBED_COLLECTION", "sessions")  # embedding-svc モデルルーティング用
COLLECTION = os.getenv("COLLECTION", "github-trending")


def dedup(repos) -> list:
    seen: set[str] = set()
    result = []
    for r in repos:
        if r.full_name and r.full_name not in seen:
            seen.add(r.full_name)
            result.append(r)
    return result


@click.command()
@click.option("--skip-ossinsight", is_flag=True, default=False)
@click.option("--skip-bestofjs", is_flag=True, default=False)
@click.option("--days-back", default=7, type=int, help="GitHub Search: 何日前まで対象")
@click.option("--dry-run", is_flag=True, default=False, help="Qdrant に書かず結果だけ表示")
def main(skip_ossinsight: bool, skip_bestofjs: bool, days_back: int, dry_run: bool):
    from collectors import bestofjs, gh_trending, github_search, ossinsight
    from ingest import ingest

    all_repos = []

    # 1. GitHub Search API
    if GITHUB_TOKEN:
        click.echo("[1/4] GitHub Search API ...")
        try:
            repos = github_search.collect(GITHUB_TOKEN, days_back=days_back)
            click.echo(f"  → {len(repos)} repos")
            all_repos.extend(repos)
        except Exception as e:
            click.echo(f"  ✗ {e}", err=True)
    else:
        click.echo("[1/4] GitHub Search API … GITHUB_TOKEN 未設定、スキップ", err=True)

    # 2. github.com/trending scrape
    click.echo("[2/4] github.com/trending ...")
    for since in ("daily", "weekly"):
        try:
            repos = gh_trending.collect(since=since)
            click.echo(f"  {since}: {len(repos)} repos")
            all_repos.extend(repos)
        except Exception as e:
            click.echo(f"  ✗ {since}: {e}", err=True)

    # 3. bestofjs.org
    if not skip_bestofjs:
        click.echo("[3/4] JS/TS (bestofjs via GitHub Search) ...")
        try:
            repos = bestofjs.collect(token=GITHUB_TOKEN, days_back=days_back)
            click.echo(f"  → {len(repos)} repos")
            all_repos.extend(repos)
        except Exception as e:
            click.echo(f"  ✗ {e}", err=True)
    else:
        click.echo("[3/4] bestofjs … スキップ")

    # 4. ossinsight.io
    if not skip_ossinsight:
        click.echo("[4/4] ossinsight.io ...")
        try:
            repos = ossinsight.collect()
            click.echo(f"  → {len(repos)} repos")
            all_repos.extend(repos)
        except Exception as e:
            click.echo(f"  ✗ {e}", err=True)
    else:
        click.echo("[4/4] ossinsight … スキップ")

    deduped = dedup(all_repos)
    click.echo(f"\n合計: {len(all_repos)} → dedup後: {len(deduped)}")

    if dry_run:
        click.echo("\n[dry-run] Qdrant への書き込みをスキップ")
        for r in deduped[:10]:
            click.echo(f"  {r.stars:>6}★  {r.full_name}  [{r.lang}]  {r.description[:60]}")
        return

    click.echo(f"\nQdrant ({COLLECTION}) へ ingest ...")
    count = ingest(deduped, QDRANT_URL, EMBED_URL, COLLECTION, EMBED_API_KEY, EMBED_COLLECTION)
    click.echo(f"完了: {count} points upserted")


if __name__ == "__main__":
    main()
