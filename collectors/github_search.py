"""GitHub Search API — 全言語トレンド (stars/updated ソート)"""
import sys
import time
from datetime import datetime, timedelta, timezone

import httpx

from models import Repo

_BASE = "https://api.github.com/search/repositories"
_MAX_RETRIES = 2


def _get_page(client: httpx.Client, params: dict, headers: dict) -> dict:
    """1 ページ取得。5xx は指数バックオフで最大 _MAX_RETRIES 回リトライ。"""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            r = client.get(_BASE, params=params, headers=headers)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            if code in (429, 403):
                reset = e.response.headers.get("X-RateLimit-Reset", "unknown")
                print(
                    f"  [github_search] rate limited (HTTP {code}, reset={reset}) — skipping",
                    file=sys.stderr,
                )
                return {}
            if 500 <= code < 600 and attempt < _MAX_RETRIES:
                wait = 2 ** attempt
                print(f"  [github_search] HTTP {code} — retry {attempt + 1}/{_MAX_RETRIES} in {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
    return {}


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
            data = _get_page(
                client,
                params={
                    "q": f"pushed:>{since} stars:>50",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 30,
                    "page": page,
                },
                headers=headers,
            )
            for item in data.get("items", []):
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
