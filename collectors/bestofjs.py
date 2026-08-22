"""JS/TS エコシステム トレンド — GitHub Search API (JavaScript/TypeScript)

bestofjs.org は公開 REST API を持たないため GitHub Search API で代替。
stars:>500 の JS/TS リポジトリを週次更新順で取得する。
"""
from datetime import datetime, timedelta, timezone

import httpx

from models import Repo

_BASE = "https://api.github.com/search/repositories"


def collect(token: str = "", days_back: int = 7, per_lang: int = 50) -> list[Repo]:
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    now = datetime.now(timezone.utc).isoformat()
    repos: list[Repo] = []

    for lang in ("JavaScript", "TypeScript"):
        try:
            r = httpx.get(
                _BASE,
                params={
                    "q": f"language:{lang} pushed:>{since} stars:>500",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": per_lang,
                },
                headers=headers,
                timeout=30.0,
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
                    source="bestofjs",
                    fetched_at=now,
                ))
        except Exception as e:
            print(f"  [bestofjs] {lang}: {e}")

    return repos
