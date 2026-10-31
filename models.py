import hashlib
import uuid
from dataclasses import dataclass


@dataclass
class Repo:
    full_name: str
    description: str
    stars: int
    lang: str | None
    topics: list[str]
    license: str | None
    source: str  # github_search | gh_trending | bestofjs | ossinsight
    fetched_at: str  # ISO8601

    def point_id(self) -> str:
        return str(uuid.UUID(bytes=hashlib.md5(self.full_name.encode()).digest()))

    def embed_text(self) -> str:
        parts = [self.full_name]
        if self.description:
            parts.append(self.description)
        if self.topics:
            parts.append(" ".join(self.topics))
        if self.lang:
            parts.append(self.lang)
        return " | ".join(parts)

    def to_payload(self) -> dict:
        return {
            "full_name": self.full_name,
            "description": self.description,
            "stars": self.stars,
            "lang": self.lang,
            "topics": self.topics,
            "license": self.license,
            "source": self.source,
            "fetched_at": self.fetched_at,
        }


@dataclass
class Post:
    """技術者コミュニティの投稿(HN/Zenn/はてブ等)。url を重複排除キーにする。"""
    url: str
    title: str
    score: int
    source: str  # hn | zenn | hatena
    fetched_at: str  # ISO8601
    discussion_url: str | None = None

    def point_id(self) -> str:
        return str(uuid.UUID(bytes=hashlib.md5(self.url.encode()).digest()))

    def embed_text(self) -> str:
        return f"{self.title} | {self.source}"

    def to_payload(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "score": self.score,
            "source": self.source,
            "fetched_at": self.fetched_at,
            "discussion_url": self.discussion_url,
            # search.py / ingest の既存インデックス・表示と互換 (Repo 用キーに写像)
            "full_name": self.title,
            "description": self.url,
            "stars": self.score,
            "lang": None,
            "license": None,
        }
