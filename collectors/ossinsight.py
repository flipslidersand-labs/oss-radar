"""ossinsight.io — トレンドリポジトリ収集

v1/trends/repos エンドポイント使用。
旧 /v1/collections/{slug}/ranking/repos は廃止済み（404）。
"""
import httpx
from datetime import datetime, timezone
from models import Repo

_BASE = "https://api.ossinsight.io/v1/trends/repos"

LANGUAGES = ["", "Go", "Rust", "Python", "TypeScript"]  # "" = 全言語


def _fetch_lang(client: httpx.Client, lang: str, now: str) -> list[Repo]:
    params: dict = {"limit": 100}
    if lang:
        params["language"] = lang

    try:
        r = client.get(_BASE, params=params)
        r.raise_for_status()
    except (httpx.HTTPStatusError, httpx.RequestError):
        return []

    repos = []
    for item in r.json().get("data", {}).get("rows", []):
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
