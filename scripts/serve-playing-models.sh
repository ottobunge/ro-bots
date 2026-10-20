#!/usr/bin/env bash
# Launch only an owned model server using existing pinned Nix assets.
set -euo pipefail
umask 077
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KIND="${1:-chat}"
case "$KIND" in
  chat) MODEL="$ROOT/models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf"; PORT="${PORT:-8300}" ;;
  clef) MODEL="$ROOT/models/Clef-Flash-Q4_K_M.gguf"; PORT="${PORT:-8302}" ;;
  *) printf '%s\n' 'Usage: serve-playing-models.sh chat|clef' >&2; exit 2 ;;
esac
BINARY="$(readlink -f "$ROOT/spikes/006-rocm-local/result")/bin/llama-server"
[[ "$BINARY" == /nix/store/* && -x "$BINARY" && -f "$MODEL" ]]
# Never kill an existing process; an occupied port fails at bind.
exec "$BINARY" -m "$MODEL" --alias "$KIND" --host 127.0.0.1 --port "$PORT" \
  -ngl 99 -c 4096 -np 1 -b 4096 -ub 4096 -fa on --no-webui --threads 8
