#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/digest.log"

MAX_RETRIES="${MAX_RETRIES:-12}"
RETRY_INTERVAL_SECONDS="${RETRY_INTERVAL_SECONDS:-300}"

cd "${PROJECT_DIR}"
mkdir -p "${LOG_DIR}"

timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

has_network() {
  local url
  for url in "https://www.baidu.com" "https://www.cloudflare.com"; do
    if curl -fsS --max-time 8 -I "${url}" >/dev/null 2>&1; then
      return 0
    fi
  done
  return 1
}

run_digest() {
  unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY
  uv run python -m signalforge_daily.digest_cli --hours 24 --top-n 15 --lang zh >>"${LOG_FILE}" 2>&1
}

for ((attempt = 1; attempt <= MAX_RETRIES; attempt++)); do
  if has_network; then
    echo "$(timestamp) network available, running digest (attempt ${attempt}/${MAX_RETRIES})" >>"${LOG_FILE}"
    run_digest
    echo "$(timestamp) digest completed" >>"${LOG_FILE}"
    exit 0
  fi

  echo "$(timestamp) no network, retry ${attempt}/${MAX_RETRIES} after ${RETRY_INTERVAL_SECONDS}s" >>"${LOG_FILE}"
  if ((attempt < MAX_RETRIES)); then
    sleep "${RETRY_INTERVAL_SECONDS}"
  fi
done

echo "$(timestamp) failed: network unavailable after ${MAX_RETRIES} retries" >>"${LOG_FILE}"
exit 1
