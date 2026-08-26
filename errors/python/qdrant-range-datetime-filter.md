---
title: "qdrant_client の Range は数値専用 — 日時フィルタは DatetimeRange を使う"
tags: [qdrant, python]
severity: medium
date: "2026-08-26"
---

## 症状

```
pydantic_core.ValidationError: 1 validation error for Range
gte
  Input should be a valid number, unable to parse string as a number
  [type=float_parsing, input_value='2026-08-20', input_type=str]
```

`FieldCondition(key="fetched_at", range=Range(gte="2026-08-20"))` で発生。

## 原因

`qdrant_client.models.Range` の `gte`/`lte` は `float` のみ受け付ける。
ISO 8601 の日時文字列を渡すと pydantic バリデーションで弾かれる。

## 解決策

`DatetimeRange` を使う。`gte` に ISO 日時文字列 or `datetime` を渡せる。

```python
from qdrant_client.models import DatetimeRange, FieldCondition

FieldCondition(key="fetched_at", range=DatetimeRange(gte="2026-08-20"))
```

`DatetimeRange` は内部で `datetime.datetime(2026, 8, 20, 0, 0)` にパースされる（テストで比較するときは `datetime` 型で照合）。

## 予防

日時ペイロードに対して Range フィルタを書くときは必ず `DatetimeRange` を使う。
数値フィールド（stars 等）は従来通り `Range` でOK。
