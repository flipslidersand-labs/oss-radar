# oss-radar

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![License](https://img.shields.io/github/license/flipslidersand-labs/oss-radar)

---

## English

GitHub trending collector & semantic search — collects OSS trends from multiple sources and stores them in Qdrant for semantic search.

### Features

- **Collect** (4 sources): GitHub Search API / github.com/trending scrape / JS-TS focused (bestofjs) / ossinsight.io
- **Ingest**: MINIPC e5 embedding → upsert into Qdrant `github-trending` collection (deduplication)
- **Search**: Natural language query + lang/license/stars-min filters for semantic search

### Directory Structure

```
oss-radar/
├── collectors/
│   ├── github_search.py   # GitHub Search API (all languages)
│   ├── gh_trending.py     # github.com/trending scrape
│   ├── bestofjs.py        # JS/TS focused (GitHub Search alternative)
│   └── ossinsight.py      # ossinsight.io trends
├── oss_radar/
│   └── query.py           # SearchClient — embed + Qdrant shared helper
├── scripts/
│   └── deploy.sh          # Auto-deploy to host (git pull + pip sync)
├── ingest.py              # embed + Qdrant upsert
├── search.py              # Semantic search CLI
├── mcp_server.py          # MCP server (search_trending tool for Claude Code)
├── main.py                # Collect + dedup + ingest orchestration
├── models.py              # Repo dataclass
├── requirements.txt
├── requirements-dev.txt   # ruff / pyright / pytest
└── ruff.toml              # lint config
```

### Setup

```bash
git clone https://github.com/flipslidersand-labs/oss-radar.git
cd oss-radar
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# Edit .env and set each value
```

### Environment Variables (.env)

| Variable | Description | Example |
|---|---|---|
| `GITHUB_TOKEN` | GitHub PAT (rate limit relief for Search API) | `ghp_xxxx` |
| `QDRANT_URL` | Qdrant connection URL | `http://localhost:6333` |
| `EMBED_URL` | embedding-svc endpoint | `http://your-embed-svc:9092/embed/batch` |
| `EMBED_API_KEY` | embedding-svc API key | `xxxx` |
| `EMBED_COLLECTION` | embedding-svc model routing | `sessions` |
| `COLLECTION` | Qdrant collection name | `github-trending` |

### Usage

```bash
# Collect all sources + Qdrant ingest
set -a && source .env && set +a
.venv/bin/python main.py

# dry-run (display results without writing to Qdrant)
.venv/bin/python main.py --dry-run

# Skip ossinsight
.venv/bin/python main.py --skip-ossinsight
```

### Search

```bash
set -a && source .env && set +a

# Semantic search
.venv/bin/python search.py "stream processing OSS for reference"

# With filters
.venv/bin/python search.py "easy to embed library" --lang Rust --limit 5
.venv/bin/python search.py "ML pipeline" --license MIT --stars-min 500

# Source / date filters
.venv/bin/python search.py "stream processing" --source ossinsight
.venv/bin/python search.py "Go framework" --since 2026-08-20
```

### MCP Server (Claude Code Integration)

Start `mcp_server.py` to use the `search_trending` tool directly from Claude Code.

Example `.claude/settings.json` registration:

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

### Cron (Auto-collect & Auto-deploy)

| cron | Schedule | Content |
|---|---|---|
| Collect | Daily 07:00 JST (22:00 UTC) | Run `main.py` → log: `/var/log/oss-radar.log` |
| Deploy | Every hour at :00 | `scripts/deploy.sh` (git pull + pip sync) → log: `/var/log/oss-radar-deploy.log` |

### Operations

#### logrotate Setup

Place rotation config for `/var/log/oss-radar.log` and `/var/log/oss-radar-deploy.log`:

```bash
sudo cp scripts/logrotate-oss-radar.conf /etc/logrotate.d/oss-radar
```

Config: weekly / rotate 4 / compress / missingok / notifempty

Verify:

```bash
sudo logrotate -d /etc/logrotate.d/oss-radar
```

#### Weekly Health Check Setup

Set the following in `~/.config/oss-radar/env`:

```bash
QDRANT_URL=http://localhost:6333
EMBED_API_URL=http://your-embed-svc:9092
COLLECTION=github-trending
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxxx/yyyy
```

Add to crontab (`crontab -e`):

```cron
0 8 * * 0 bash ~/oss-radar/scripts/oss-radar-health.sh >> /var/log/oss-radar-health.log 2>&1
```

Checks:

- embed service (`EMBED_API_URL/health`) connectivity
- Qdrant `github-trending` collection `points_count` vs previous run
- Discord warning if no new ingests

### Notes

- `bestofjs.org` has no public REST API, so GitHub Search API (JS/TS) is used as an alternative
- embedding-svc requires `X-API-Key` header + `collection`/`mode` fields

---

## 日本語

GitHub trending collector & semantic search — 複数ソースから OSS トレンドを収集し、Qdrant に蓄積してセマンティック検索するツール。

### 主な機能

- **収集** (4ソース): GitHub Search API / github.com/trending scrape / JS-TS特化 / ossinsight.io
- **ingest**: e5 embedding → Qdrant `github-trending` コレクションへ upsert (重複排除)
- **検索**: 自然言語クエリ + lang/license/stars-min フィルタによるセマンティック検索

### ディレクトリ構成

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
│   └── deploy.sh          # ホスト自動デプロイ (git pull + pip sync)
├── ingest.py              # embed + Qdrant upsert
├── search.py              # セマンティック検索 CLI
├── mcp_server.py          # MCP サーバー (Claude Code から search_trending ツールを呼ぶ)
├── main.py                # 収集 + dedup + ingest オーケストレーション
├── models.py              # Repo データクラス
├── requirements.txt
├── requirements-dev.txt   # ruff / pyright / pytest
└── ruff.toml              # lint 設定
```

### セットアップ

```bash
git clone https://github.com/flipslidersand-labs/oss-radar.git
cd oss-radar
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# .env を編集して各値を設定
```

### 環境変数 (.env)

| 変数 | 説明 | 例 |
|---|---|---|
| `GITHUB_TOKEN` | GitHub PAT (Search API レート制限緩和) | `ghp_xxxx` |
| `QDRANT_URL` | Qdrant 接続先 | `http://localhost:6333` |
| `EMBED_URL` | embedding-svc エンドポイント | `http://your-embed-svc:9092/embed/batch` |
| `EMBED_API_KEY` | embedding-svc API キー | `xxxx` |
| `EMBED_COLLECTION` | embedding-svc モデルルーティング用 | `sessions` |
| `COLLECTION` | Qdrant コレクション名 | `github-trending` |

### 実行方法

```bash
# 全ソース収集 + Qdrant ingest
set -a && source .env && set +a
.venv/bin/python main.py

# dry-run (Qdrant に書かず結果表示)
.venv/bin/python main.py --dry-run

# ossinsight スキップ
.venv/bin/python main.py --skip-ossinsight
```

### 検索

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

### MCP サーバー (Claude Code 連携)

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

### MINIPC cron (自動収集・自動デプロイ)

| cron | スケジュール | 内容 |
|---|---|---|
| 収集 | 毎日 07:00 JST (22:00 UTC) | `main.py` 実行 → ログ: `/var/log/oss-radar.log` |
| デプロイ | 毎時 0 分 | `scripts/deploy.sh` (git pull + pip sync) → ログ: `/var/log/oss-radar-deploy.log` |

### 運用手順

#### logrotate デプロイ

`/var/log/oss-radar.log` および `/var/log/oss-radar-deploy.log` のローテーション設定を配置:

```bash
sudo cp scripts/logrotate-oss-radar.conf /etc/logrotate.d/oss-radar
```

設定内容: weekly / rotate 4 / compress / missingok / notifempty

動作確認:

```bash
sudo logrotate -d /etc/logrotate.d/oss-radar
```

#### 週次ヘルスチェック登録方法

`~/.config/oss-radar/env` に以下を設定:

```bash
QDRANT_URL=http://localhost:6333
EMBED_API_URL=http://your-embed-svc:9092
COLLECTION=github-trending
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxxx/yyyy
```

crontab に追加 (`crontab -e`):

```cron
0 8 * * 0 bash ~/oss-radar/scripts/oss-radar-health.sh >> /var/log/oss-radar-health.log 2>&1
```

チェック内容:

- embed サービス (`EMBED_API_URL/health`) の疎通確認
- Qdrant `github-trending` コレクションの `points_count` を前回実行時と比較
- 0 件以上増加していない場合は Discord に警告通知

### 注意事項

- `bestofjs.org` は公開 REST API を持たないため、GitHub Search API (JS/TS) で代替
- embedding-svc は `X-API-Key` ヘッダー + `collection`/`mode` フィールド必須
