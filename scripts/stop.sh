#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PIDFILE="${PIDFILE:-data/server.pid}"
TMUX_SESSION="${TMUX_SESSION:-ai-receptionist-runtime}"

if command -v tmux >/dev/null 2>&1 && tmux has-session -t "${TMUX_SESSION}" >/dev/null 2>&1; then
  tmux kill-session -t "${TMUX_SESSION}"
  rm -f "${PIDFILE}"
  echo "Stopped tmux runtime session ${TMUX_SESSION}"
  exit 0
fi

if [ ! -f "${PIDFILE}" ]; then
  echo "No pidfile at ${PIDFILE}. If the server is running in a terminal, stop it with Ctrl-C."
  exit 0
fi

PID="$(cat "${PIDFILE}")"
if printf "%s" "${PID}" | grep -q "^tmux:"; then
  echo "No matching tmux session for ${PID}"
  rm -f "${PIDFILE}"
  exit 0
fi

if kill -0 "${PID}" >/dev/null 2>&1; then
  kill "${PID}"
  echo "Stopped runtime pid ${PID}"
else
  echo "Runtime pid ${PID} is not running"
fi

rm -f "${PIDFILE}"
