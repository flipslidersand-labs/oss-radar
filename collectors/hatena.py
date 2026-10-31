"""はてなブックマーク — テクノロジー人気/新着エントリ RSS (RSS 1.0 / RDF, キー不要)"""
import logging
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

import httpx

from models import Post

logger = logging.getLogger(__name__)

FEEDS = ["https://b.hatena.ne.jp/hotentry/it.rss", "https://b.hatena.ne.jp/entrylist/it.rss"]

_NS = {"rss": "http://purl.org/rss/1.0/", "hatena": "http://www.hatena.ne.jp/info/xmlns#"}


def _parse(xml_text: str, now: str) -> list[Post]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.warning("hatena parse error: %s", e)
        return []
    posts = []
    for item in root.findall("rss:item", _NS):
        title = (item.findtext("rss:title", namespaces=_NS) or "").strip()
        link = (item.findtext("rss:link", namespaces=_NS) or "").strip()
        if not title or not link:
            continue
        try:
            score = int(item.findtext("hatena:bookmarkcount", namespaces=_NS) or 0)
        except ValueError:
            score = 0
        posts.append(Post(
            url=link, title=title, score=score, source="hatena", fetched_at=now,
            discussion_url=f"https://b.hatena.ne.jp/entry/{link}",
        ))
    return posts


def collect() -> list[Post]:
    now = datetime.now(UTC).isoformat()
    posts: list[Post] = []
    with httpx.Client(timeout=30.0, headers={"User-Agent": "oss-radar/1.0"}) as client:
        for url in FEEDS:
            try:
                r = client.get(url)
                r.raise_for_status()
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                logger.warning("hatena fetch error %s: %s", url, e)
                continue
            posts.extend(_parse(r.text, now))
    logger.info("hatena: %d posts", len(posts))
    return posts
