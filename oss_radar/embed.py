"""embedding-svc への POST の共通ヘルパー

timeout と HTTP クライアントの持ち方(都度生成 / 使い回し)は呼び出し側が決める。
ingest は 180s で都度生成(大きなバッチ)、検索は 60s で使い回し(低レイテンシ)。
"""

import httpx


def post_embed(
    http: httpx.Client,
    url: str,
    texts: list[str],
    collection: str,
    mode: str,
    api_key: str = "",
) -> list[list[float]]:
    """texts を embed してベクトル列を返す。mode は "index"(登録) か "search"(検索)。"""
    headers = {"X-API-Key": api_key} if api_key else {}
    r = http.post(url, json={"texts": texts, "collection": collection, "mode": mode}, headers=headers)
    r.raise_for_status()
    return r.json()["vectors"]
