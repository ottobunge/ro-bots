#!/usr/bin/env bash
# Ordinary named-volume Compose routing; runtime/database preparation is separate.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$repo_dir"
operation="${1:-status}"
if (( $# )); then shift; fi
if [[ "$operation" == prepare ]]; then
  args=()
  if [[ -n "${WORLD_STAGE:-}" ]]; then args+=(--destination "$WORLD_STAGE"); fi
  exec uv run --offline --no-sync python -m robots.adapters.world_prepare_cli "${args[@]}" "$@"
fi
if [[ "$operation" == wipe ]]; then operation=wipe-test; fi
args=()
if [[ -n "${WORLD_STAGE:-}" ]]; then args+=(--inputs-file "$WORLD_STAGE/compose-inputs.json"); fi
exec uv run --offline --no-sync python -m robots.adapters.world_compose "${operation}" "${args[@]}" "$@"
