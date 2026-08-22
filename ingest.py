"""Embed + Qdrant upsert"""
import os
import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)
from models import Repo

VECTOR_SIZE = 768  # MINIPC e5 model output dim
BATCH_SIZE = 64


def _embed(texts: list[str], embed_url: str) -> list[list[float]]:
    with httpx.Client(timeout=60.0) as client:
        r = client.post(embed_url, json={"texts": texts})
        r.raise_for_status()
    data = r.json()
    return data.get("embeddings", data)


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
) -> int:
    if not repos:
        return 0

    client = QdrantClient(url=qdrant_url)
    _ensure_collection(client, collection)

    upserted = 0
    for i in range(0, len(repos), BATCH_SIZE):
        batch = repos[i : i + BATCH_SIZE]
        texts = [r.embed_text() for r in batch]
        vectors = _embed(texts, embed_url)

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
