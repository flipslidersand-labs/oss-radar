from dataclasses import dataclass, field
from typing import Optional
import hashlib
import uuid


@dataclass
class Repo:
    full_name: str
    description: str
    stars: int
    lang: Optional[str]
    topics: list[str]
    license: Optional[str]
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
