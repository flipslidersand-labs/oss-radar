---
title: "qdrant-client 1.19 で client.search() が廃止"
tags: [qdrant, python, api-change]
severity: medium
date: "2026-08-22"
---

## 症状

```
AttributeError: 'QdrantClient' object has no attribute 'search'
```

qdrant-client 1.19 をインストールすると `client.search()` が存在しない。

## 原因

qdrant-client 1.x 系でベクトル検索 API が刷新され、`search()` は `query_points()` に置き換わった。

## 解決策

```python
# 旧 (1.9 以前)
results = client.search(
    collection_name=collection,
    query_vector=vec,
    query_filter=filt,
    limit=limit,
    with_payload=True,
)

# 新 (1.10+)
results = client.query_points(
    collection_name=collection,
    query=vec,
    query_filter=filt,
    limit=limit,
    with_payload=True,
).points  # .points でリストを取り出す
```

## 予防

`requirements.txt` にバージョン上限を入れるか、インストール後に `query_points` の有無を確認する。
