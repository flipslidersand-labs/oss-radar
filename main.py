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
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

import click
from dotenv import load_dotenv

from oss_radar.env_check import insecure_embed_url_warning

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
EMBED_URL = os.getenv("EMBED_URL", "http://localhost:9092/embed/batch")
EMBED_API_KEY = os.getenv("EMBED_API_KEY", "")
EMBED_COLLECTION = os.getenv("EMBED_COLLECTION", "sessions")  # embedding-svc モデルルーティング用
COLLECTION = os.getenv("COLLECTION", "github-trending")


def _check_env(dry_run: bool) -> None:
    warnings = []
    if not dry_run and not EMBED_API_KEY:
        warnings.append("EMBED_API_KEY が未設定です。embedding-svc の認証に失敗します (.env を確認してください)")
    insecure = insecure_embed_url_warning(EMBED_URL, EMBED_API_KEY)
    if not dry_run and insecure:
        warnings.append(insecure)
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


@dataclass
class Source:
    """収集ソース 1 つ。ソース追加は main() の `sources` に 1 件足すだけでよい。

    variants: (ラベル, 収集関数)。ラベルが空なら単独実行、あれば `name/label` で個別に失敗を記録する
              (例: gh_trending の daily / weekly)。
    skip: (理由, stderr に出すか)。指定時は収集せず件数 0 とする。
    """

    name: str
    title: str
    variants: list[tuple[str, Callable[[], list]]]
    skip: tuple[str, bool] | None = field(default=None)


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

    sources = [
        Source(
            "github_search",
            "GitHub Search API",
            [("", lambda: github_search.collect(GITHUB_TOKEN, days_back=days_back))],
            skip=None if GITHUB_TOKEN else ("GITHUB_TOKEN 未設定、スキップ", True),
        ),
        Source(
            "gh_trending",
            "github.com/trending",
            [(since, lambda since=since: gh_trending.collect(since=since)) for since in ("daily", "weekly")],
        ),
        Source(
            "bestofjs",
            "JS/TS (bestofjs via GitHub Search)",
            [("", lambda: bestofjs.collect(token=GITHUB_TOKEN, days_back=days_back))],
            skip=("スキップ", False) if skip_bestofjs else None,
        ),
        Source(
            "ossinsight",
            "ossinsight.io",
            [("", ossinsight.collect)],
            skip=("スキップ", False) if skip_ossinsight else None,
        ),
    ]

    for i, src in enumerate(sources, 1):
        prefix = f"[{i}/{len(sources)}]"
        source_counts[src.name] = 0
        if src.skip:
            reason, to_err = src.skip
            click.echo(f"{prefix} {src.name} … {reason}", err=to_err)
            continue
        click.echo(f"{prefix} {src.title} ...")
        t0 = time.monotonic()
        succeeded = False
        for label, collect in src.variants:
            try:
                repos = collect()
            except Exception as e:
                click.echo(f"  ✗ {label + ': ' if label else ''}{e}", err=True)
                errors.append({"source": f"{src.name}/{label}" if label else src.name, "error": str(e)})
                continue
            succeeded = True
            click.echo(f"  {label}: {len(repos)} repos" if label else f"  → {len(repos)} repos")
            all_repos.extend(repos)
            source_counts[src.name] += len(repos)
        if succeeded:
            source_stats[src.name] = (source_counts[src.name], time.monotonic() - t0)

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
    count = ingest(deduped, QDRANT_URL, EMBED_URL, COLLECTION, EMBED_API_KEY, EMBED_COLLECTION, QDRANT_API_KEY)
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
            record_snapshot(QDRANT_URL, source, n, round(elapsed, 3), QDRANT_API_KEY)
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
        "date": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
