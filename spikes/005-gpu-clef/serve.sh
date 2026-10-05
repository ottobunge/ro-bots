#!/usr/bin/env bash
# framework-agents: persistent Clef servers on Heavengraph (2x Quadro RTX 8000).
#   port 8091: Clef-Flash Q4_K_M  on GPU 0   (decision endpoint /v1/systemone)
#   port 8092: Clef-27B  Q4_K_M   on GPU 1   (decision endpoint /v1/systemone)
# Bound to 0.0.0.0; reachable from the LAN/VPN as
#   http://192.168.1.156:8091  (also 10.8.0.3:8091)
#   http://192.168.1.156:8092  (also 10.8.0.3:8092)
# Idempotent: kills existing llama-server processes first. nohup + setsid so it
# survives the SSH session.
set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$DIR/result/bin/llama-server"
FLASH="$DIR/Clef-Flash-Q4_K_M.gguf"
B27="$DIR/Clef-27B-Q4_K_M.gguf"

if [ ! -x "$BIN" ]; then
  echo "missing $BIN — run: nix build .#llama-cpp-clef-cuda --out-link ./result"
  exit 1
fi

pkill -f llama-server 2>/dev/null
sleep 2

start() { # $1 model, $2 port, $3 log, extra args in $4..
  local model="$1" port="$2" log="$3"; shift 3
  setsid nohup "$BIN" -m "$model" --port "$port" --host 0.0.0.0 \
    -ngl 99 -sm none -c 65536 -np 8 -b 4096 -ub 4096 -fa on --no-webui "$@" \
    > "$log" 2>&1 < /dev/null &
  echo "started $model on :$port (pid $!, log $log)"
}

# -sm none -mg N pins each model to exactly one GPU.
start "$FLASH" 8091 /tmp/clef-flash-8091.log -mg 0
[ -f "$B27" ] && start "$B27" 8092 /tmp/clef-27b-8092.log -mg 1

sleep 6
nvidia-smi --query-gpu=index,name,memory.used --format=csv,noheader
