"""環境変数の既定値(定数のみ)。

各エントリポイント(main / search / mcp_server / community)が `os.getenv(NAME, DEFAULT_*)` で使う。
既定値を変えるときはここだけを直す。読込そのものは各モジュールに残してある(テストがモジュール属性を patch するため)。
"""

DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_EMBED_URL = "http://localhost:9092/embed/batch"
DEFAULT_EMBED_COLLECTION = "sessions"  # embedding-svc のモデルルーティング用
DEFAULT_COLLECTION = "github-trending"
DEFAULT_COMMUNITY_COLLECTION = "community-posts"
