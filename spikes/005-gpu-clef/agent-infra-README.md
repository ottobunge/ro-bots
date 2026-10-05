# framework-agents — GPU model serving (Heavengraph)

Reproducible CUDA llama.cpp (Clef-capable, ggml-org/llama.cpp @ a7fb71f — the
commit with the native `POST /v1/systemone` endpoint) plus launch scripts that
keep the Clef decision servers running as standing infrastructure.

## Layout
- `flake.nix` — `packages.llama-cpp-clef-cuda` (nixpkgs llama-cpp packaging,
  `cudaSupport = true`, Turing sm_75) and `apps.serve` / `apps.serve-flash`.
- `llama.cpp/` — vendored ggml-org/llama.cpp @ a7fb71f (nixpkgs 0.5.0 predates
  the Clef merge PR #29831; source build required until nixpkgs bumps).
- `serve.sh` — (re)start llama-server instances; logs under /tmp.
- `Clef-Flash-Q4_K_M.gguf` (6.5 GB), `Clef-27B-Q4_K_M.gguf` (19.2 GB) — weights.

## Build

```bash
cd /datamirror/otto/repos/framework-agents
nix build .#llama-cpp-clef-cuda --out-link ./result
```

First build compiles CUDA kernels (~10 min); cached afterwards.

## Start / restart the servers

```bash
cd /datamirror/otto/repos/framework-agents
nix run .#serve          # or: bash serve.sh
```

| Port | GPU | Model |
|---|---|---|
| 8091 | GPU 0 (`-ngl 99`) | Clef-Flash Q4_K_M, 8 slots |
| 8092 | GPU 1 (`-ngl 99`) | Clef-27B Q4_K_M, 8 slots |

From the local host (ro-bots box), the reachable URLs are:

- `http://192.168.1.156:8091` — Clef-Flash (LAN, verified; 10.8.0.3:8091 also answers)
- `http://192.168.1.156:8092` — Clef-27B

`HEAVENGRAPH_CLEF_URL=http://192.168.1.156:8091` is the standing Clef decision
endpoint for the e2e/runner; the 27B lives at `...:8092`.

To survive a reboot: re-run `nix run .#serve` (nohup'd, idempotent — it kills
existing llama-server processes first). A systemd --user unit is provided under
`clef-serve.service` if heavengraph allows lingering
(`systemctl --user enable --now clef-serve.service`; requires
`loginctl enable-linger otto`).
