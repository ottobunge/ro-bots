#!/usr/bin/env bash
# Spike 006: Clef-Flash on the Radeon 890M (gfx1150) via ROCm/HIP llama.cpp.
# Serves /v1/systemone on 127.0.0.1:8093 (mirrors spike 001's :8091 layout).
#
# VRAM note: the 890M's ~16GB is shared with the desktop, but llama.cpp HIP
# on this APU does NOT allocate from the 512MB dedicated VRAM — it maps
# open/system memory (GTT aperture, 46GB): ~6.5GB weights + ~3.7GB process
# RSS observed. Check with:
#   nix shell nixpkgs#rocmPackages.rocm-smi -c rocm-smi --showmeminfo gtt
#
# gfx1150 env (kept as no-op safety): HSA_OVERRIDE_GFX_VERSION=11.0.0,
# HIP_FORCE_DEV_KERNARG=1. HIP backend loads and runs with or without them.
#
# Server flags (verified 2026-10-05, llama.cpp a7fb71f, ROCm 7.2.3):
#  - The spike-001 4-slot config (-c 16384 -np 4) SEGFAULTS during HIP model
#    load on this build (SIGSEGV right after the embeddings init warning,
#    repeatedly). -np 2 / -c 8192 works. Batch-8 latency is prefill-dominated
#    either way — extra slots just queue on the single APU.
#  - -b/-ub 4096 required: clef reads embeddings, so the default ub=512
#    aborts on >512-token requests ("encoder requires n_ubatch >= n_tokens").
set -euo pipefail
cd "$(dirname "$0")"

MODEL="${MODEL:-/home/otto/dev/ro-bots/models/Clef-Flash-Q4_K_M.gguf}"
PORT="${PORT:-8093}"

export HSA_OVERRIDE_GFX_VERSION="${HSA_OVERRIDE_GFX_VERSION:-11.0.0}"
export HIP_FORCE_DEV_KERNARG=1

pkill -f "llama-server.*--port ${PORT}" 2>/dev/null || true
sleep 1

exec ./result/bin/llama-server \
  -m "$MODEL" \
  --port "$PORT" --host 127.0.0.1 \
  -ngl 99 \
  -c 8192 -np 2 -b 4096 -ub 4096 \
  -fa on --no-webui \
  --threads 8
