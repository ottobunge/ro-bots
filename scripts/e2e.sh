#!/usr/bin/env bash
# Fail-closed E2E wrapper. No KEEP/TICKS/CLEF/environment opt-in authorizes
# lifecycle work; the Python planner remains inert until ownership is observed.
set -euo pipefail

printf '%s\n' '[e2e] blocked: isolated lifecycle ownership and gameplay acceptance are unverified' >&2
exit 2
