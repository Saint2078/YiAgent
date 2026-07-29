#!/usr/bin/env bash
# Seed YIAGENT_HOME then exec yiagent (Hermes-style stage2).
set -euo pipefail

export YIAGENT_HOME="${YIAGENT_HOME:-/opt/data}"
mkdir -p "$YIAGENT_HOME"/{workspace,sessions,logs,save}

if [[ ! -f "$YIAGENT_HOME/config.yaml" ]]; then
  yiagent setup >/dev/null
fi
if [[ ! -f "$YIAGENT_HOME/.env" ]]; then
  yiagent setup >/dev/null
fi

# Drop privileges if YIAGENT_UID set and running as root
if [[ "$(id -u)" == "0" && -n "${YIAGENT_UID:-}" ]]; then
  gid="${YIAGENT_GID:-$YIAGENT_UID}"
  chown -R "${YIAGENT_UID}:${gid}" "$YIAGENT_HOME" 2>/dev/null || true
fi

if [[ "$#" -eq 0 ]]; then
  set -- chat
fi

exec yiagent "$@"
