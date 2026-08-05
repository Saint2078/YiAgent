#!/usr/bin/env bash
# 应急：宿主机直接跑 bridge（主路径见 README · docker compose · DEC-044）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

resolve_node() {
  if [[ -x /opt/homebrew/bin/node ]]; then
    echo /opt/homebrew/bin/node
    return
  fi
  if command -v node >/dev/null 2>&1; then
    command -v node
    return
  fi
  echo "node not found · prefer: docker compose up -d --build" >&2
  exit 1
}

NODE="$(resolve_node)"
if [[ ! -d "$ROOT/node_modules/@cursor/sdk" ]]; then
  echo "missing deps · npm install && npm rebuild sqlite3（或改用 Compose 镜像）" >&2
  exit 1
fi

export HOST="${HOST:-127.0.0.1}"
exec "$NODE" server.mjs
