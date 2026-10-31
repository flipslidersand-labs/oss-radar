"""Qdrant コレクション作成の共通ヘルパー"""
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import VectorParams


def ensure_collection(client: QdrantClient, name: str, vectors_config: VectorParams) -> None:
    """コレクションが無ければ作成する。並行プロセスが先に作成した場合(409)は成功扱い。"""
    existing = {c.name for c in client.get_collections().collections}
    if name in existing:
        return
    try:
        client.create_collection(collection_name=name, vectors_config=vectors_config)
    except UnexpectedResponse as e:
        if e.status_code != 409:
            raise
