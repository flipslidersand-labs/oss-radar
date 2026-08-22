---
title: "MINIPC embedding-svc の認証形式・リクエスト仕様"
tags: [embedding, minipc, api, auth]
severity: medium
date: "2026-08-22"
---

## 症状

```
401 Unauthorized: 'Authorization: Bearer <key>' では弾かれる
422 Unprocessable Entity: mode="query" は無効
KeyError: "embeddings" (レスポンスキーが違う)
```

## 原因

MINIPC の embedding-svc (`:9092`) は doc-ingest 向けに独自仕様で実装されている。

## 解決策

```python
# 正しいリクエスト形式
headers = {"X-API-Key": api_key}  # Bearer ではなく X-API-Key
body = {
    "texts": [...],
    "collection": "sessions",  # embedding-svc 側のモデルルーティング用
    "mode": "index",           # index (格納時) or search (検索時)。"query" は無効
}
response = httpx.post(url, json=body, headers=headers)
vectors = response.json()["vectors"]  # "embeddings" ではなく "vectors"
```

## 予防

doc-ingest の `core/qdrant.py` が正本仕様。新規プロジェクトで使う際はそこを参照する。
API キーは `ssh minipc sudo cat /etc/embedding-svc/env` で取得。
