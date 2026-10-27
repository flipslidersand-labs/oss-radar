"""環境変数の安全性チェック(起動時警告用)"""
from urllib.parse import urlparse

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def insecure_embed_url_warning(embed_url: str, api_key: str) -> str | None:
    """API キーを http:// 経由でローカル以外へ送る設定なら警告文を返す。問題なければ None。"""
    if not api_key:
        return None
    parsed = urlparse(embed_url)
    if parsed.scheme != "http" or parsed.hostname in _LOCAL_HOSTS:
        return None
    return (
        f"EMBED_URL ({embed_url}) が http:// のため EMBED_API_KEY が平文で送信されます。"
        "https:// の利用を推奨します(社内ネットワークでも盗聴リスクあり)"
    )
