"""Zenn — トレンド + トピック別 RSS (キー不要)。RSS に点数は無いので score=0。"""
import logging
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

import httpx

from models import Post

logger = logging.getLogger(__name__)

_BASE = "https://zenn.dev"
TOPICS = ["", "llm", "claudecode", "rust", "go", "python", "typescript", "githubactions", "kubernetes"]  # "" = トレンド


def _feed_url(topic: str) -> str:
    return f"{_BASE}/topics/{topic}/feed" if topic else f"{_BASE}/feed"


def _parse(xml_text: str, now: str) -> list[Post]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.warning("zenn parse error: %s", e)
        return []
    posts = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        posts.append(Post(url=link, title=title, score=0, source="zenn", fetched_at=now, discussion_url=None))
    return posts


def collect() -> list[Post]:
    now = datetime.now(UTC).isoformat()
    posts: list[Post] = []
    with httpx.Client(timeout=30.0, headers={"User-Agent": "oss-radar/1.0"}) as client:
        for topic in TOPICS:
            try:
                r = client.get(_feed_url(topic))
                r.raise_for_status()
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                logger.warning("zenn fetch error topic=%r: %s", topic or "trend", e)
                continue
            posts.extend(_parse(r.text, now))
    logger.info("zenn: %d posts", len(posts))
    return posts
