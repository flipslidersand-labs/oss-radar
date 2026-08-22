"""ossinsight.io — コレクション別トレンドリポジトリ"""
import httpx
from datetime import datetime, timezone
from models import Repo

_BASE = "https://api.ossinsight.io/v1/collections/{slug}/ranking/repos"

COLLECTIONS = [
    "open-source-database",
    "javascript-framework",
    "go-framework",
    "rust-framework",
    "ai-infra",
    "devops-tool",
]


def _fetch_collection(client: httpx.Client, slug: str, now: str) -> list[Repo]:
    try:
        r = client.get(
            _BASE.format(slug=slug),
            params={"period": "past_28_days", "orderBy": "stars", "direction": "desc"},
        )
        r.raise_for_status()
    except httpx.HTTPStatusError:
        return []

    repos = []
    for item in r.json().get("data", {}).get("rows", []):
        repos.append(Repo(
            full_name=f"{item.get('repo_name', '')}",
            description=item.get("description") or "",
            stars=item.get("total_score", 0),
            lang=item.get("primary_language"),
            topics=[slug],
            license=None,
            source="ossinsight",
            fetched_at=now,
        ))
    return repos


def collect() -> list[Repo]:
    now = datetime.now(timezone.utc).isoformat()
    repos: list[Repo] = []

    with httpx.Client(timeout=30.0) as client:
        for slug in COLLECTIONS:
            repos.extend(_fetch_collection(client, slug, now))

    return repos
