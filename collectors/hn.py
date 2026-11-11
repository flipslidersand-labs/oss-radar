"""Hacker News — front page 収集 (Algolia API, キー不要)"""

import logging
from datetime import UTC, datetime

import httpx

from models import Post

logger = logging.getLogger(__name__)

_URL = "https://hn.algolia.com/api/v1/search"


def _parse(hits: list[dict], now: str) -> list[Post]:
    posts = []
    for h in hits:
        title = h.get("title") or ""
        oid = h.get("objectID", "")
        if not title or not oid:
            continue
        discussion = f"https://news.ycombinator.com/item?id={oid}"
        posts.append(
            Post(
                url=h.get("url") or discussion,  # Ask HN 等は url 無し
                title=title,
                score=int(h.get("points") or 0),
                source="hn",
                fetched_at=now,
                discussion_url=discussion,
            )
        )
    return posts


def collect(hits_per_page: int = 100) -> list[Post]:
    now = datetime.now(UTC).isoformat()
    try:
        with httpx.Client(timeout=30.0, headers={"User-Agent": "oss-radar/1.0"}) as client:
            r = client.get(_URL, params={"tags": "front_page", "hitsPerPage": hits_per_page})
            r.raise_for_status()
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        logger.warning("hn fetch error: %s", e)
        return []
    posts = _parse(r.json().get("hits", []), now)
    logger.info("hn: %d posts", len(posts))
    return posts
