#!/usr/bin/env bash
# e2e-assert wrapper: the modest first bar over the newest e2e window receipt.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "${SCRIPT_DIR}/env.sh"
e2e_load_inputs

FIXTURE="${E2E_STAGE}/fixture/fixture.json"
MANIFEST="${E2E_STAGE}/host-manifest.json"
[[ -f "${FIXTURE}" && -f "${MANIFEST}" ]] || {
  echo "e2e-assert: REFUSED: stage fixture/manifest missing; run task e2e-init first" >&2
  exit 2
}

exec "${E2E_REPO}/.venv/bin/python" "${SCRIPT_DIR}/assert.py" \
  "${E2E_REPO}" "${FIXTURE}" "${MANIFEST}" "${E2E_DURATION_S}"
