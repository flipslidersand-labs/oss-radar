"""github.com/trending スクレイパー — 全言語トレンドページ"""
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from models import Repo

_BASE = "https://github.com/trending"


def _parse_stars(text: str) -> int:
    text = text.strip().replace(",", "").lower()
    if text.endswith("k"):
        try:
            return int(float(text[:-1]) * 1000)
        except ValueError:
            return 0
    try:
        return int(text)
    except ValueError:
        return 0


def collect(lang: str = "", since: str = "daily") -> list[Repo]:
    """
    lang: "" = 全言語, "python", "go", "rust" など
    since: "daily" | "weekly" | "monthly"
    """
    url = _BASE
    if lang:
        url = f"{_BASE}/{lang}"
    now = datetime.now(timezone.utc).isoformat()

    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        r = client.get(url, params={"since": since}, headers={"Accept": "text/html"})
        r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    repos: list[Repo] = []

    for article in soup.select("article.Box-row"):
        name_tag = article.select_one("h2 a")
        if not name_tag:
            continue
        full_name = name_tag.get("href", "").lstrip("/")

        desc_tag = article.select_one("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        lang_tag = article.select_one('[itemprop="programmingLanguage"]')
        language = lang_tag.get_text(strip=True) if lang_tag else None

        stars_tag = article.select_one('a[href$="/stargazers"]')
        stars = _parse_stars(stars_tag.get_text()) if stars_tag else 0

        repos.append(Repo(
            full_name=full_name,
            description=description,
            stars=stars,
            lang=language,
            topics=[],
            license=None,
            source="gh_trending",
            fetched_at=now,
        ))

    return repos
