#!/usr/bin/env bash
# scripts/oss-radar-health.sh
# oss-radar ヘルスチェック: Qdrant 件数・embed サービス疎通 → Discord 通知
# 環境変数: ~/.config/oss-radar/env に DISCORD_WEBHOOK_URL 等を定義

set -euo pipefail

ENV_FILE="${HOME}/.config/oss-radar/env"
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck source=/dev/null
  source "${ENV_FILE}"
fi

QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
EMBED_API_URL="${EMBED_API_URL:-http://localhost:9092}"
COLLECTION="${COLLECTION:-github-trending}"
QDRANT_API_KEY="${QDRANT_API_KEY:-}"
DISCORD_WEBHOOK_URL="${DISCORD_WEBHOOK_URL:-}"

# --------------------------------------------------------------------------
# ユーティリティ
# --------------------------------------------------------------------------

notify() {
  local message="$1"
  if [[ -z "${DISCORD_WEBHOOK_URL}" ]]; then
    echo "[WARN] DISCORD_WEBHOOK_URL 未設定 — 標準エラーに出力します" >&2
    echo "${message}" >&2
    return
  fi
  # Webhook URL は機密(トークン含む)のため curl の引数に載せない(ps / /proc/<pid>/cmdline 露出対策)。
  # URL は -K - で標準入力の config として渡し、payload は jq で JSON エスケープして一時ファイル経由で渡す。
  local payload
  payload="$(mktemp)"
  jq -n --arg content "${message}" '{content: $content}' > "${payload}"
  local code
  code=$(printf 'url = "%s"\n' "${DISCORD_WEBHOOK_URL}" |
    curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
      -H "Content-Type: application/json" \
      --data-binary "@${payload}" \
      -K - || true)
  rm -f "${payload}"
  if [[ ! "${code}" =~ ^2[0-9][0-9]$ ]]; then
    echo "[ERROR] Discord 通知に失敗しました (HTTP ${code:-000})" >&2
    FAILED=1
  fi
}

# 失敗を 1 件でも検知したら最後に exit 1 (cron / 監視が拾えるようにする)
FAILED=0

# --------------------------------------------------------------------------
# 1. embed サービス疎通チェック
# --------------------------------------------------------------------------

echo "[INFO] embed サービス疎通チェック: ${EMBED_API_URL}/health"
EMBED_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
  "${EMBED_API_URL}/health" 2>/dev/null || echo "000")

if [[ "${EMBED_STATUS}" != "200" ]]; then
  MSG="⚠️ oss-radar: embed サービスが応答しません (${EMBED_API_URL}/health → HTTP ${EMBED_STATUS})"
  echo "[ERROR] ${MSG}" >&2
  notify "${MSG}"
  FAILED=1
else
  echo "[INFO] embed サービス OK (HTTP ${EMBED_STATUS})"
fi

# --------------------------------------------------------------------------
# 2. Qdrant コレクション件数チェック
# --------------------------------------------------------------------------

echo "[INFO] Qdrant 件数チェック: ${QDRANT_URL}/collections/${COLLECTION}"
# QDRANT_API_KEY は ps に露出させないよう -K - (stdin config) で渡す
# curl config の二重引用符内では \ と " が特殊なので先にエスケープする
KEY_ESC=${QDRANT_API_KEY//\\/\\\\}
KEY_ESC=${KEY_ESC//\"/\\\"}
COLLECTION_INFO=$(printf 'header = "api-key: %s"\n' "${KEY_ESC}" |
  curl -s --max-time 10 -K - \
    "${QDRANT_URL}/collections/${COLLECTION}" 2>/dev/null || echo "")

if [[ -z "${COLLECTION_INFO}" ]]; then
  MSG="⚠️ oss-radar: Qdrant (${QDRANT_URL}) に接続できません"
  echo "[ERROR] ${MSG}" >&2
  notify "${MSG}"
  exit 1
fi

CURRENT_COUNT=$(echo "${COLLECTION_INFO}" | jq -r '.result.points_count | numbers' 2>/dev/null || true)
if [[ ! "${CURRENT_COUNT}" =~ ^[0-9]+$ ]]; then
  # エラー JSON など。0 とみなしてキャッシュへ保存すると停滞判定が恒久的に無効化されるため保存しない
  MSG="⚠️ oss-radar: Qdrant から points_count を取得できません (collection: ${COLLECTION})"
  echo "[ERROR] ${MSG}" >&2
  notify "${MSG}"
  exit 1
fi
echo "[INFO] 現在の points_count: ${CURRENT_COUNT}"

# 前回カウントをキャッシュファイルで保持
CACHE_DIR="${HOME}/.cache/oss-radar"
CACHE_FILE="${CACHE_DIR}/last_points_count"
mkdir -p "${CACHE_DIR}"

PREVIOUS_COUNT=0
if [[ -f "${CACHE_FILE}" ]]; then
  PREVIOUS_COUNT=$(cat "${CACHE_FILE}" 2>/dev/null || echo "0")
fi
echo "[INFO] 前回の points_count: ${PREVIOUS_COUNT}"

# 現在のカウントをキャッシュに保存
echo "${CURRENT_COUNT}" > "${CACHE_FILE}"

# 前日比 0 増チェック
if [[ "${CURRENT_COUNT}" -le "${PREVIOUS_COUNT}" ]] && [[ "${PREVIOUS_COUNT}" -gt 0 ]]; then
  MSG="⚠️ oss-radar: 0件 ingest が続いています (points_count: ${PREVIOUS_COUNT} → ${CURRENT_COUNT})"
  echo "[WARN] ${MSG}" >&2
  notify "${MSG}"
else
  echo "[INFO] ingest 正常 (${PREVIOUS_COUNT} → ${CURRENT_COUNT})"
fi

if [[ "${FAILED}" -ne 0 ]]; then
  echo "[ERROR] ヘルスチェックで異常を検知しました" >&2
  exit 1
fi
echo "[INFO] ヘルスチェック完了"
