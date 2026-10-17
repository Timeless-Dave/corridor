#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
root_dir="$PWD"
[[ -x .venv/bin/python && -d web/node_modules ]] || { echo 'Install Python and web dependencies first; see README.md.' >&2; exit 1; }
cleanup() {
  kill "$api_pid" "$web_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
(cd "$root_dir/api" && exec ../.venv/bin/uvicorn main:app --host 127.0.0.1 --port "${API_PORT:-8000}" --workers 1) &
api_pid=$!
(cd "$root_dir/web" && export CORRIDOR_API_URL="http://127.0.0.1:${API_PORT:-8000}" && exec npm run dev -- --port "${WEB_PORT:-3001}") &
web_pid=$!
echo "Corridor: http://localhost:${WEB_PORT:-3001} (synthetic data; Ctrl+C stops both services)"
while kill -0 "$api_pid" 2>/dev/null && kill -0 "$web_pid" 2>/dev/null; do sleep 1; done
exit 1
