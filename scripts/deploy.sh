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

# pip 成功時のみ requirements.txt の hash を印として書く。
# pull だけ成功して pip が失敗しても、印が不一致なので次回 pip を再実行する。
STAMP=".venv/.requirements.sha256"
current_hash() { sha256sum requirements.txt | cut -d' ' -f1; }
pip_needed() { [ ! -f .venv/bin/pip ] || [ ! -f "${STAMP}" ] || [ "$(cat "${STAMP}")" != "$(current_hash)" ]; }

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "${LOCAL}" != "${REMOTE}" ]; then
    log "[deploy] updating ${LOCAL:0:7} → ${REMOTE:0:7}"
    git pull origin main --ff-only --quiet
    log "[deploy] pull done"
elif ! pip_needed; then
    log "[deploy] already up-to-date (${LOCAL:0:7})"
    exit 0
fi

# pip sync (venv がなければ作成してから install)
if [ ! -f .venv/bin/pip ]; then
    log "[deploy] .venv not found — creating venv"
    python3 -m venv .venv
    log "[deploy] venv created"
fi
.venv/bin/pip install -r requirements.txt -q
current_hash > "${STAMP}"
log "[deploy] pip sync done"

log "[deploy] complete"
