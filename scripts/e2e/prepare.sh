#!/usr/bin/env bash
# e2e-prepare: stage the private isolated e2e world (files only, no containers).
# Writes runtime/conf assets (baked with the e2e ports), bootstrap SQL, fresh
# secrets and compose-inputs.json under run/worlds/e2e/e2e-isolated (git-ignored).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "${SCRIPT_DIR}/env.sh"

exec env PYTHONPATH="${E2E_REPO}/src" \
  "${E2E_REPO}/.venv/bin/python" "${SCRIPT_DIR}/prepare.py" "${E2E_STAGE}"
