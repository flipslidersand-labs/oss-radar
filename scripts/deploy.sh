#!/usr/bin/env bash
# MINIPC 自動デプロイスクリプト — cron から呼び出される
# 毎時 0 分に git pull + pip sync を実行する
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_FILE="/var/log/oss-radar-deploy.log"
TIMESTAMP="$(date '+%Y-%m-%dT%H:%M:%S%z')"

log() { echo "${TIMESTAMP} $*" | tee -a "${LOG_FILE}"; }

cd "${REPO_DIR}"

# リモートの変更をフェッチ
git fetch origin main --quiet

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "${LOCAL}" = "${REMOTE}" ]; then
    log "[deploy] already up-to-date (${LOCAL:0:7})"
    exit 0
fi

log "[deploy] updating ${LOCAL:0:7} → ${REMOTE:0:7}"
git pull origin main --ff-only --quiet
log "[deploy] pull done"

# pip sync (差分のみ)
if [ -f .venv/bin/pip ]; then
    .venv/bin/pip install -r requirements.txt -q
    log "[deploy] pip sync done"
else
    log "[deploy] .venv not found — skip pip sync"
fi

log "[deploy] complete"
