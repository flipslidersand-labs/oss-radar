"""embed クエリ・フィルタ構築の共通ヘルパー

search.py と mcp_server.py の両方から使用する。
"""
import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue, Range


def embed_query(
    text: str,
    embed_url: str,
    api_key: str = "",
    embed_collection: str = "sessions",
) -> list[float]:
    headers = {"X-API-Key": api_key} if api_key else {}
    with httpx.Client(timeout=60.0) as client:
        r = client.post(
            embed_url,
            json={"texts": [text], "collection": embed_collection, "mode": "search"},
            headers=headers,
        )
        r.raise_for_status()
    return r.json()["vectors"][0]


def build_filter(lang: str | None, license_: str | None, stars_min: int) -> Filter | None:
    conditions = []
    if lang:
        conditions.append(FieldCondition(key="lang", match=MatchValue(value=lang)))
    if license_:
        conditions.append(FieldCondition(key="license", match=MatchValue(value=license_)))
    if stars_min > 0:
        conditions.append(FieldCondition(key="stars", range=Range(gte=stars_min)))
    return Filter(must=conditions) if conditions else None


class SearchClient:
    """embed + Qdrant を束ねた再利用可能な検索クライアント（singleton 用途）"""

    def __init__(
        self,
        qdrant_url: str,
        embed_url: str,
        api_key: str = "",
        embed_collection: str = "sessions",
    ) -> None:
        self._embed_url = embed_url
        self._api_key = api_key
        self._embed_collection = embed_collection
        self._qdrant = QdrantClient(url=qdrant_url)

    def search(
        self,
        query: str,
        collection: str,
        lang: str | None = None,
        license_: str | None = None,
        stars_min: int = 0,
        limit: int = 10,
    ) -> list:
        vec = embed_query(query, self._embed_url, self._api_key, self._embed_collection)
        filt = build_filter(lang, license_, stars_min)
        return self._qdrant.query_points(
            collection_name=collection,
            query=vec,
            query_filter=filt,
            limit=limit,
            with_payload=True,
        ).points
