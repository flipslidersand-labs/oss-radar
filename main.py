#!/usr/bin/env python3
"""収集 + ingest オーケストレーション

Usage:
    python main.py                    # 全ソース収集
    python main.py --skip-ossinsight  # ossinsight をスキップ
    python main.py --dry-run          # dedup 結果だけ表示、Qdrant には書かない
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

import click
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
EMBED_URL = os.getenv("EMBED_URL", "http://192.168.68.63:9092/embed/batch")
EMBED_API_KEY = os.getenv("EMBED_API_KEY", "")
EMBED_COLLECTION = os.getenv("EMBED_COLLECTION", "sessions")  # embedding-svc モデルルーティング用
COLLECTION = os.getenv("COLLECTION", "github-trending")


def _check_env(dry_run: bool) -> None:
    warnings = []
    if not dry_run and not EMBED_API_KEY:
        warnings.append("EMBED_API_KEY が未設定です。embedding-svc の認証に失敗します (.env を確認してください)")
    if not dry_run and "192.168.68" in EMBED_URL and not os.getenv("EMBED_URL"):
        warnings.append(f"EMBED_URL がデフォルト値 ({EMBED_URL}) のままです。外部ネットワークからは到達できません")
    for w in warnings:
        click.echo(f"[WARN] {w}", err=True)


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
    from oss_radar.stats import record_snapshot

    _check_env(dry_run)
    t_start = time.monotonic()
    all_repos = []
    source_counts: dict[str, int] = {}
    source_stats: dict[str, tuple[int, float]] = {}
    errors: list[dict] = []

    # 1. GitHub Search API
    if GITHUB_TOKEN:
        click.echo("[1/4] GitHub Search API ...")
        try:
            t0 = time.monotonic()
            repos = github_search.collect(GITHUB_TOKEN, days_back=days_back)
            elapsed = time.monotonic() - t0
            click.echo(f"  → {len(repos)} repos")
            all_repos.extend(repos)
            source_counts["github_search"] = len(repos)
            source_stats["github_search"] = (len(repos), elapsed)
        except Exception as e:
            click.echo(f"  ✗ {e}", err=True)
            errors.append({"source": "github_search", "error": str(e)})
            source_counts["github_search"] = 0
    else:
        click.echo("[1/4] GitHub Search API … GITHUB_TOKEN 未設定、スキップ", err=True)
        source_counts["github_search"] = 0

    # 2. github.com/trending scrape
    click.echo("[2/4] github.com/trending ...")
    source_counts["gh_trending"] = 0
    t0 = time.monotonic()
    for since in ("daily", "weekly"):
        try:
            repos = gh_trending.collect(since=since)
            click.echo(f"  {since}: {len(repos)} repos")
            all_repos.extend(repos)
            source_counts["gh_trending"] += len(repos)
        except Exception as e:
            click.echo(f"  ✗ {since}: {e}", err=True)
            errors.append({"source": f"gh_trending/{since}", "error": str(e)})
    source_stats["gh_trending"] = (source_counts["gh_trending"], time.monotonic() - t0)

    # 3. bestofjs.org
    if not skip_bestofjs:
        click.echo("[3/4] JS/TS (bestofjs via GitHub Search) ...")
        try:
            t0 = time.monotonic()
            repos = bestofjs.collect(token=GITHUB_TOKEN, days_back=days_back)
            elapsed = time.monotonic() - t0
            click.echo(f"  → {len(repos)} repos")
            all_repos.extend(repos)
            source_counts["bestofjs"] = len(repos)
            source_stats["bestofjs"] = (len(repos), elapsed)
        except Exception as e:
            click.echo(f"  ✗ {e}", err=True)
            errors.append({"source": "bestofjs", "error": str(e)})
            source_counts["bestofjs"] = 0
    else:
        click.echo("[3/4] bestofjs … スキップ")
        source_counts["bestofjs"] = 0

    # 4. ossinsight.io
    if not skip_ossinsight:
        click.echo("[4/4] ossinsight.io ...")
        try:
            t0 = time.monotonic()
            repos = ossinsight.collect()
            elapsed = time.monotonic() - t0
            click.echo(f"  → {len(repos)} repos")
            all_repos.extend(repos)
            source_counts["ossinsight"] = len(repos)
            source_stats["ossinsight"] = (len(repos), elapsed)
        except Exception as e:
            click.echo(f"  ✗ {e}", err=True)
            errors.append({"source": "ossinsight", "error": str(e)})
            source_counts["ossinsight"] = 0
    else:
        click.echo("[4/4] ossinsight … スキップ")
        source_counts["ossinsight"] = 0

    deduped = dedup(all_repos)
    click.echo(f"\n合計: {len(all_repos)} → dedup後: {len(deduped)}")

    if dry_run:
        click.echo("\n[dry-run] Qdrant への書き込みをスキップ")
        for r in deduped[:10]:
            click.echo(f"  {r.stars:>6}★  {r.full_name}  [{r.lang}]  {r.description[:60]}")
        _emit_summary(
            source_counts=source_counts,
            total_raw=len(all_repos),
            deduped=len(deduped),
            upserted=0,
            errors=errors,
            elapsed_sec=time.monotonic() - t_start,
        )
        return

    click.echo(f"\nQdrant ({COLLECTION}) へ ingest ...")
    count = ingest(deduped, QDRANT_URL, EMBED_URL, COLLECTION, EMBED_API_KEY, EMBED_COLLECTION)
    click.echo(f"完了: {count} points upserted")

    _emit_summary(
        source_counts=source_counts,
        total_raw=len(all_repos),
        deduped=len(deduped),
        upserted=count,
        errors=errors,
        elapsed_sec=time.monotonic() - t_start,
    )

    # weekly snapshot を oss-radar-stats コレクションへ記録
    click.echo("\n[stats] oss-radar-stats へ snapshot 記録 ...")
    for source, (n, elapsed) in source_stats.items():
        try:
            record_snapshot(QDRANT_URL, source, n, round(elapsed, 3))
            click.echo(f"  {source}: {n} count, {elapsed:.1f}s")
        except Exception as e:
            click.echo(f"  ✗ stats upsert ({source}): {e}", err=True)


def _emit_summary(
    *,
    source_counts: dict[str, int],
    total_raw: int,
    deduped: int,
    upserted: int,
    errors: list[dict],
    elapsed_sec: float,
) -> None:
    summary = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": source_counts,
        "total_raw": total_raw,
        "deduped": deduped,
        "upserted": upserted,
        "errors": errors,
        "elapsed_sec": round(elapsed_sec, 2),
    }
    sys.stderr.write(json.dumps(summary, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
