"""GitHub Search API — 全言語トレンド (stars/updated ソート)"""
from datetime import datetime, timedelta, timezone

import httpx

from models import Repo

_BASE = "https://api.github.com/search/repositories"


def collect(token: str, days_back: int = 7, pages: int = 3) -> list[Repo]:
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    now = datetime.now(timezone.utc).isoformat()
    repos: list[Repo] = []

    with httpx.Client(timeout=30.0) as client:
        for page in range(1, pages + 1):
            r = client.get(
                _BASE,
                params={
                    "q": f"pushed:>{since} stars:>50",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 30,
                    "page": page,
                },
                headers=headers,
            )
            r.raise_for_status()
            for item in r.json().get("items", []):
                repos.append(Repo(
                    full_name=item["full_name"],
                    description=item.get("description") or "",
                    stars=item["stargazers_count"],
                    lang=item.get("language"),
                    topics=item.get("topics", []),
                    license=(item.get("license") or {}).get("spdx_id"),
                    source="github_search",
                    fetched_at=now,
                ))

    return repos
