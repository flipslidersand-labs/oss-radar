# oss-radar

GitHub trending collector & semantic search — 複数ソースから OSS トレンドを収集し、Qdrant に蓄積してセマンティック検索するツール。

## 主な機能


- **収集** (4ソース): GitHub Search API / github.com/trending scrape / JS-TS特化 / ossinsight.io
- **ingest**: MINIPC e5 embedding → Qdrant `github-trending` コレクションへ upsert (重複排除)
- **検索**: 自然言語クエリ + lang/license/stars-min フィルタによるセマンティック検索

## ディレクトリ構成

```
oss-radar/
├── collectors/
│   ├── github_search.py   # GitHub Search API (全言語)
│   ├── gh_trending.py     # github.com/trending スクレイプ
│   ├── bestofjs.py        # JS/TS 特化 (GitHub Search 代替)
│   └── ossinsight.py      # ossinsight.io トレンド
├── oss_radar/
│   └── query.py           # SearchClient — embed + Qdrant 共通ヘルパー
├── scripts/
│   └── deploy.sh          # MINIPC 自動デプロイ (git pull + pip sync)
├── ingest.py              # embed + Qdrant upsert
├── search.py              # セマンティック検索 CLI
├── mcp_server.py          # MCP サーバー (Claude Code から search_trending ツールを呼ぶ)
├── main.py                # 収集 + dedup + ingest オーケストレーション
├── models.py              # Repo データクラス
├── requirements.txt
├── requirements-dev.txt   # ruff / pyright / pytest
└── ruff.toml              # lint 設定
```

## セットアップ

```bash
git clone https://github.com/flipslidersand-labs/oss-radar.git
cd oss-radar
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# .env を編集して各値を設定
```

## 環境変数 (.env)

| 変数 | 説明 | 例 |
|---|---|---|
| `GITHUB_TOKEN` | GitHub PAT (Search API レート制限緩和) | `ghp_xxxx` |
| `QDRANT_URL` | Qdrant 接続先 | `http://localhost:6333` |
| `EMBED_URL` | embedding-svc エンドポイント | `http://192.168.68.63:9092/embed/batch` |
| `EMBED_API_KEY` | embedding-svc API キー | `xxxx` |
| `EMBED_COLLECTION` | embedding-svc モデルルーティング用 | `sessions` |
| `COLLECTION` | Qdrant コレクション名 | `github-trending` |

## 実行方法

```bash
# 全ソース収集 + Qdrant ingest
set -a && source .env && set +a
.venv/bin/python main.py

# dry-run (Qdrant に書かず結果表示)
.venv/bin/python main.py --dry-run

# ossinsight スキップ
.venv/bin/python main.py --skip-ossinsight
```

## 検索

```bash
set -a && source .env && set +a

# セマンティック検索
.venv/bin/python search.py "設計参考になるストリーム処理OSS"

# フィルタ付き
.venv/bin/python search.py "組み込みやすいライブラリ" --lang Rust --limit 5
.venv/bin/python search.py "MLパイプライン" --license MIT --stars-min 500

# 収集元・期間フィルタ
.venv/bin/python search.py "stream processing" --source ossinsight
.venv/bin/python search.py "Go framework" --since 2026-08-20
```

## MCP サーバー (Claude Code 連携)

`mcp_server.py` を起動すると、Claude Code から `search_trending` ツールで直接検索できる。

`.claude/settings.json` への登録例:

```json
{
  "mcpServers": {
    "oss-radar": {
      "command": "python",
      "args": ["/path/to/oss-radar/mcp_server.py"],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "EMBED_URL": "http://your-embed-svc:9092/embed/batch",
        "EMBED_API_KEY": "xxxx",
        "EMBED_COLLECTION": "sessions",
        "COLLECTION": "github-trending"
      }
    }
  }
}
```

## MINIPC cron (自動収集・自動デプロイ)

| cron | スケジュール | 内容 |
|---|---|---|
| 収集 | 毎日 07:00 JST (22:00 UTC) | `main.py` 実行 → ログ: `/var/log/oss-radar.log` |
| デプロイ | 毎時 0 分 | `scripts/deploy.sh` (git pull + pip sync) → ログ: `/var/log/oss-radar-deploy.log` |

## 注意事項

- `bestofjs.org` は公開 REST API を持たないため、GitHub Search API (JS/TS) で代替
- embedding-svc は `X-API-Key` ヘッダー + `collection`/`mode` フィールド必須
