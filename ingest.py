"""Embed + Qdrant upsert"""
import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from models import Repo

VECTOR_SIZE = 768  # MINIPC e5 model output dim
BATCH_SIZE = 64


def _embed(
    texts: list[str], embed_url: str, api_key: str = "", embed_collection: str = "sessions"
) -> list[list[float]]:
    headers = {"X-API-Key": api_key} if api_key else {}
    with httpx.Client(timeout=180.0) as client:
        r = client.post(
            embed_url,
            json={"texts": texts, "collection": embed_collection, "mode": "index"},
            headers=headers,
        )
        r.raise_for_status()
    return r.json()["vectors"]


def _ensure_collection(client: QdrantClient, collection: str) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if collection not in existing:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


def ingest(
    repos: list[Repo],
    qdrant_url: str,
    embed_url: str,
    collection: str,
    embed_api_key: str = "",
    embed_collection: str = "sessions",
) -> int:
    if not repos:
        return 0

    client = QdrantClient(url=qdrant_url)
    _ensure_collection(client, collection)

    upserted = 0
    for i in range(0, len(repos), BATCH_SIZE):
        batch = repos[i : i + BATCH_SIZE]
        texts = [r.embed_text() for r in batch]
        vectors = _embed(texts, embed_url, embed_api_key, embed_collection)
        if len(vectors) != len(batch):
            raise ValueError(
                f"embed mismatch at batch {i//BATCH_SIZE}: sent {len(batch)} texts, got {len(vectors)} vectors"
            )

        points = [
            PointStruct(
                id=repo.point_id(),
                vector=vec,
                payload=repo.to_payload(),
            )
            for repo, vec in zip(batch, vectors)
        ]
        client.upsert(collection_name=collection, points=points)
        upserted += len(points)
        print(f"  upserted {upserted}/{len(repos)}")

    return upserted
