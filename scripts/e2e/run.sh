#!/usr/bin/env bash
# e2e-run: ONE bounded verification window (default 300s, hard ceiling 330s)
# against the isolated e2e world, using the reviewed window composition
# (engagement_window34: fail-fast decision preflight, then the emission
# operator). Receipts land under .work/playing-grind-emission/evidence/ in THIS
# worktree. The decision backend is the heavengraph Clef; a real-shape decide
# probe runs inside the composition before the window opens.
#
# Task semantics: this task owns the WINDOW, not the verdict. It exits 0 when
# the window ran and produced its receipt (whatever the receipt's own passed
# value — e2e-assert judges acceptance); it exits nonzero only when no window
# ran (refusals, backend preflight blocker, crash without a receipt).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "${SCRIPT_DIR}/env.sh"
e2e_load_inputs
e2e_require_up

if ! awk -v d="${E2E_DURATION_S}" 'BEGIN { exit !(d > 0 && d <= 330) }'; then
  echo "e2e-run: REFUSED: duration ${E2E_DURATION_S}s outside 1..330s e2e ceiling" >&2
  exit 2
fi

MANIFEST="${E2E_STAGE}/host-manifest.json"
[[ -f "${MANIFEST}" ]] || {
  echo "e2e-run: REFUSED: no host manifest at ${MANIFEST}; run task e2e-init first" >&2
  exit 2
}

RUNTIME_ROOT="${E2E_REPO}/.work/runtime/ro-bots-e2e"
[[ -f "${RUNTIME_ROOT}/db/map_cache.dat" && -f "${RUNTIME_ROOT}/db/pre-re/mob_db.yml" ]] || {
  echo "e2e-run: REFUSED: runtime root ${RUNTIME_ROOT} lacks db/map_cache.dat or db/pre-re/mob_db.yml" >&2
  exit 2
}

echo "== e2e-run: backend probes =="
curl -fsS -m 8 "${E2E_DECISION_URL%/v1/systemone}/health" >/dev/null \
  && echo "  decision backend /health: 200" || {
  echo "e2e-run: FAIL: decision backend ${E2E_DECISION_URL} /health not ok" >&2
  exit 1
}
curl -fsS -m 8 "${E2E_CHAT_URL%/v1/chat/completions}/v1/models" >/dev/null \
  && echo "  chat backend /v1/models: 200" || {
  echo "e2e-run: FAIL: chat backend ${E2E_CHAT_URL} not answering" >&2
  exit 1
}

# The window's in-process WorldFeed must not collide with any other window
# (the reviewed test-world windows use the default 8400).
WORLDFEED_PORT=8402
if e2e_port_busy "${WORLDFEED_PORT}"; then
  echo "e2e-run: REFUSED: worldfeed port ${WORLDFEED_PORT} is already in use" >&2
  exit 2
fi

MEMORY_ROOT="${E2E_REPO}/.work/e2e-run/memory"
# The memory journal requires an owner-private root (0700) and refuses otherwise.
mkdir -p -m 700 "${MEMORY_ROOT}"
chmod 700 "${MEMORY_ROOT}" 2>/dev/null || true
mkdir -p "${E2E_REPO}/.work/playing-grind-emission/evidence"

echo "== e2e-run: window ${E2E_DURATION_S}s (pacer 6s, playground, worldfeed ${WORLDFEED_PORT}) =="
cd "${E2E_REPO}"
RECEIPT_MARK="$(date +%s)"
set +e
PYTHONPATH="src:.work/playing-grind-emission:.work/playing-grind-killchain:.work/playing-grind-killcommit:.work/engagement-diagnosis:.work/commitment-cadence" \
  "${E2E_REPO}/.venv/bin/python" -B -c "import engagement_window34; raise SystemExit(engagement_window34.main())" \
  --manifest "${MANIFEST}" \
  --runtime-root "${RUNTIME_ROOT}" \
  --memory-root "${MEMORY_ROOT}" \
  --decision-url "${E2E_DECISION_URL}" \
  --chat-url "${E2E_CHAT_URL}" \
  --worldfeed-port "${WORLDFEED_PORT}" \
  --duration "${E2E_DURATION_S}" \
  --playground \
  --pacer-every-s 6.0
RC=$?
set -e

EVIDENCE="${E2E_REPO}/.work/playing-grind-emission/evidence"
RECEIPT="$(find "${EVIDENCE}" -maxdepth 1 -name 'receipt-*.json' -newermt "@${RECEIPT_MARK}" \
  -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)"
if [[ -z "${RECEIPT}" ]]; then
  echo "e2e-run: FAIL: window exited ${RC} without a receipt under ${EVIDENCE}" \
    "(a preflight blocker writes preflight-*.json and opens no window)" >&2
  exit 1
fi

"${E2E_REPO}/.venv/bin/python" - "${RECEIPT}" <<'PY'
import json
import sys

receipt = json.load(open(sys.argv[1], encoding="utf-8"))
print(f"e2e-run: receipt {sys.argv[1]}")
print(f"  window verdict (transport-only + floor): passed={receipt.get('passed')}")
for persona, entry in sorted((receipt.get("agents") or {}).items()):
    calls = (entry.get("decision_calls") or {}).get("count")
    dispatched = (entry.get("dispatched_actions") or {}).get("count") or {}
    diag = entry.get("runtime_diagnostic") or {}
    print(
        f"  {persona}: transport={entry.get('transport_state')} "
        f"floor={entry.get('engagement_floor')} decisions={calls} "
        f"dispatched={sum(int(v or 0) for v in dispatched.values())} "
        f"pos={diag.get('position')} on {diag.get('map_name')}"
    )
PY
echo "e2e-run: window exit code ${RC}; acceptance is e2e-assert's call"
exit 0
