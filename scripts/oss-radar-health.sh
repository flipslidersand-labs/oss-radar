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
  curl -s -o /dev/null -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -d "{\"content\": \"${message}\"}" \
    "${DISCORD_WEBHOOK_URL}" || true
}

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
else
  echo "[INFO] embed サービス OK (HTTP ${EMBED_STATUS})"
fi

# --------------------------------------------------------------------------
# 2. Qdrant コレクション件数チェック
# --------------------------------------------------------------------------

echo "[INFO] Qdrant 件数チェック: ${QDRANT_URL}/collections/${COLLECTION}"
COLLECTION_INFO=$(curl -s --max-time 10 \
  "${QDRANT_URL}/collections/${COLLECTION}" 2>/dev/null || echo "")

if [[ -z "${COLLECTION_INFO}" ]]; then
  MSG="⚠️ oss-radar: Qdrant (${QDRANT_URL}) に接続できません"
  echo "[ERROR] ${MSG}" >&2
  notify "${MSG}"
  exit 1
fi

CURRENT_COUNT=$(echo "${COLLECTION_INFO}" | jq -r '.result.points_count // 0' 2>/dev/null || echo "0")
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

echo "[INFO] ヘルスチェック完了"
