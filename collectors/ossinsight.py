"""ossinsight.io — トレンドリポジトリ収集

v1/trends/repos エンドポイント使用。
旧 /v1/collections/{slug}/ranking/repos は廃止済み（404）。
"""
import logging
from datetime import datetime, timezone

import httpx

from models import Repo

logger = logging.getLogger(__name__)

_BASE = "https://api.ossinsight.io/v1/trends/repos"

LANGUAGES = ["", "Go", "Rust", "Python", "TypeScript"]  # "" = 全言語


def _fetch_lang(client: httpx.Client, lang: str, now: str) -> list[Repo]:
    params: dict = {"limit": 100}
    if lang:
        params["language"] = lang

    try:
        r = client.get(_BASE, params=params)
        r.raise_for_status()
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        logger.warning("ossinsight fetch error lang=%r: %s", lang or "all", e)
        return []

    # ossinsight の Warning ヘッダーを検出してログに記録
    # 例: "199 - \"degraded data: star-event derived ranking unavailable\""
    warning = r.headers.get("warning", "")
    if warning:
        logger.warning("ossinsight API warning lang=%r: %s", lang or "all", warning)

    rows = r.json().get("data", {}).get("rows", [])
    if not rows:
        logger.warning("ossinsight returned 0 rows lang=%r (warning=%r)", lang or "all", warning or "none")
        return []

    repos = []
    for item in rows:
        full_name = item.get("repo_name", "")
        if not full_name:
            continue
        try:
            stars = int(item.get("stars", 0) or 0)
        except (ValueError, TypeError):
            stars = 0
        repos.append(Repo(
            full_name=full_name,
            description=item.get("description") or "",
            stars=stars,
            lang=item.get("primary_language"),
            topics=[],
            license=None,
            source="ossinsight",
            fetched_at=now,
        ))
    return repos


def collect() -> list[Repo]:
    now = datetime.now(timezone.utc).isoformat()
    repos: list[Repo] = []

    with httpx.Client(timeout=30.0) as client:
        for lang in LANGUAGES:
            repos.extend(_fetch_lang(client, lang, now))

    return repos
