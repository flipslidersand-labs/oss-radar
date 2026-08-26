"""weekly snapshot: 収集件数を Qdrant oss-radar-stats コレクションへ upsert"""
import hashlib
from datetime import date

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

STATS_COLLECTION = "oss-radar-stats"
# ダミーベクトル（統計用途なので意味的類似度検索は不要）
_DUMMY_VECTOR = [0.0]


def _ensure_stats_collection(client: QdrantClient) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if STATS_COLLECTION not in existing:
        client.create_collection(
            collection_name=STATS_COLLECTION,
            vectors_config=VectorParams(size=1, distance=Distance.COSINE),
        )


def _make_point_id(date_str: str, source: str) -> int:
    """sha256(date + source) の先頭 16 文字を整数化"""
    hex_str = hashlib.sha256((date_str + source).encode()).hexdigest()[:16]
    return int(hex_str, 16)


def record_snapshot(
    qdrant_url: str,
    source: str,
    count: int,
    elapsed_sec: float,
) -> None:
    """収集統計を oss-radar-stats コレクションに upsert する。

    Args:
        qdrant_url: Qdrant のベース URL
        source: 収集ソース名 (例: "github_search")
        count: 収集件数
        elapsed_sec: 収集にかかった秒数
    """
    today = date.today().isoformat()
    client = QdrantClient(url=qdrant_url)
    _ensure_stats_collection(client)

    point_id = _make_point_id(today, source)
    client.upsert(
        collection_name=STATS_COLLECTION,
        points=[
            PointStruct(
                id=point_id,
                vector=_DUMMY_VECTOR,
                payload={
                    "date": today,
                    "source": source,
                    "count": count,
                    "elapsed_sec": elapsed_sec,
                },
            )
        ],
    )
