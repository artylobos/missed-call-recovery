#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-8787}"
BASE_URL="${BASE_URL:-http://127.0.0.1:${PORT}}"
PIDFILE="${PIDFILE:-data/server.pid}"
LOGFILE="${LOGFILE:-data/server.log}"
TMUX_SESSION="${TMUX_SESSION:-ai-receptionist-runtime}"

mkdir -p data

if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
  echo "Runtime already healthy at ${BASE_URL}"
else
  echo "Starting runtime at ${BASE_URL}"
  if command -v tmux >/dev/null 2>&1; then
    if tmux has-session -t "${TMUX_SESSION}" >/dev/null 2>&1; then
      tmux kill-session -t "${TMUX_SESSION}"
    fi
    tmux new-session -d -s "${TMUX_SESSION}" "cd ${ROOT}; PYTHONPATH=src PORT=${PORT} python3 -u -m ai_receptionist_autopilot.server >>${LOGFILE} 2>&1"
    echo "tmux:${TMUX_SESSION}" >"${PIDFILE}"
  else
    nohup env PYTHONPATH=src PORT="${PORT}" python3 -u -m ai_receptionist_autopilot.server >>"${LOGFILE}" 2>&1 < /dev/null &
    echo "$!" >"${PIDFILE}"
  fi

  ready=0
  for _ in $(seq 1 40); do
    if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 0.25
  done

  if [ "${ready}" != "1" ]; then
    echo "Runtime did not become healthy. Last log lines:"
    tail -40 "${LOGFILE}" || true
    exit 1
  fi
fi

BASE_URL="${BASE_URL}" python3 scripts/smoke.py

echo "Autopilot runtime ready: ${BASE_URL}"
echo "Admin endpoints: GET ${BASE_URL}/leads and /events"
echo "Set ADMIN_API_TOKEN before exposing this server publicly."
