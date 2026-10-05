#!/usr/bin/env bash
# Spike 005-gpu-clef: start Clef servers on heavengraph GPUs.
# Clef-Flash on GPU0 (port 8091), Clef-27B split row across both GPUs (8092),
# Clef-Flash alone on GPU1 (8093) as the no-split alternative.
# All bound 0.0.0.0 so the local host can reach them over LAN/VPN.
set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$DIR/result/bin/llama-server"
MODELS=/datamirror/otto/repos/framework-agents
FLASH="$MODELS/Clef-Flash-Q4_K_M.gguf"
B27="$MODELS/Clef-27B-Q4_K_M.gguf"

pkill -f llama-server 2>/dev/null && sleep 3

if [ ! -x "$BIN" ]; then echo "missing $BIN — run: nix build .#llama-cpp-clef-cuda --out-link ./result"; exit 1; fi

if [ -f "$FLASH" ]; then
  nohup "$BIN" -m "$FLASH" --port 8091 --host 0.0.0.0 \
    -ngl 99 -c 65536 -np 8 -b 4096 -ub 4096 -fa on --no-webui \
    > /tmp/clef-gpu-flash.log 2>&1 &
  echo "Clef-Flash (GPU0)  -> :8091  pid $!  log /tmp/clef-gpu-flash.log"
else
  echo "missing $FLASH"
fi

if [ -f "$B27" ]; then
  nohup "$BIN" -m "$B27" --port 8092 --host 0.0.0.0 \
    -ngl 99 -sm row -c 65536 -np 8 -b 4096 -ub 4096 -fa on --no-webui \
    > /tmp/clef-gpu-27b.log 2>&1 &
  echo "Clef-27B (row split) -> :8092  pid $!  log /tmp/clef-gpu-27b.log"
else
  echo "missing $B27 (download Clef-27B GGUF to $MODELS to enable)"
fi

sleep 5
nvidia-smi --query-gpu=index,name,memory.used --format=csv
