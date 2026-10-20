{
  # Spike 006-rocm-local (ro-bots): Clef-Flash on the local Radeon 890M (gfx1150)
  # via ROCm/HIP llama.cpp, for the ADR-012 local-GPU decision row.
  #
  # Usage:
  #   nix build .#llama-cpp-clef-rocm --out-link ./result
  #   ./start_server.sh           # llama-server on 127.0.0.1:8093, -ngl 99
  #
  # Why this path: nixpkgs already packages `llama-cpp-rocm` 0.5.0 with
  # -DGGML_HIP=TRUE and a HIP arch list that includes gfx1150 (verified with
  # `nix eval nixpkgs#llama-cpp-rocm.cmakeFlags`), so we reuse nixpkgs'
  # rocmPackages.7.2.3 closure (hipblas/rocblas/clr) instead of building ROCm
  # from source. BUT nixpkgs 0.5.0 (tag v0.5.0, 2026-09-23) predates the Clef
  # merge (PR #29831, 2026-10-03): no tools/server/server-decision.cpp, no
  # /v1/systemone — exactly as spike 001 found for the CPU build. So we take
  # nixpkgs' llama-cpp-rocm packaging and swap in the same Clef-capable source
  # as spike 001 (vendored ../001-clef-local/llama.cpp @ a7fb71f), keeping the
  # GGML_HIP + hipClang toolchain flags nixpkgs computes for us.
  #
  # gfx1150 note: the 890M is officially unsupported by upstream ROCm (which
  # targets gfx110x), but nixpkgs 7.2.3 ships gfx1150 code objects and llama.cpp
  # HIP runs on it. If hipblaslt kernels misbehave, set
  # HSA_OVERRIDE_GFX_VERSION=11.0.0 (or 11.5.0) in start_server.sh — an env
  # override only, no rebuild needed.
  inputs.nixpkgs.url = "nixpkgs";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
      # Vendored Clef-capable llama.cpp (ggml-org master @ a7fb71f, PR #29831).
      clefSrc = ../001-clef-local/llama.cpp;
    in
    {
      devShells = forAll (pkgs: {
        default = pkgs.mkShell {
          packages = with pkgs; [
            cmake
            ninja
            rocmPackages.rocm-smi
            git
            curl
          ];
        };
      });

      packages = forAll (pkgs: {
        # nixpkgs' llama-cpp-rocm packaging (GGML_HIP=TRUE, HIP arches incl.
        # gfx1150, rocmPackages 7.2.3) with the Clef-capable master source.
        # GGML_NATIVE=OFF stays: a generic CPU fallback backend is fine, the
        # HIP backend carries the hot path (-ngl 99).
        llama-cpp-clef-rocm = (pkgs.llama-cpp-rocm.override { }).overrideAttrs (old: {
          pname = "llama-cpp-clef-rocm";
          version = "0.5.0-clef-a7fb71f-rocm";
          src = pkgs.lib.cleanSourceWith {
            src = clefSrc;
            filter = path: type:
              !(type == "directory" && (pkgs.lib.hasSuffix "/build" path));
          };
          # master's webui package-lock differs from 0.5.0's pinned npmDepsHash;
          # we run with --no-webui, so drop the npm ui build entirely.
          cmakeFlags = (old.cmakeFlags or [ ]) ++ [
            "-DLLAMA_BUILD_WEBUI=OFF"
            "-DLLAMA_BUILD_UI=OFF"
            "-DGGML_HIP=ON"
            "-DGGML_HIP_GRAPHS=ON"
            "-DAMDGPU_TARGETS=gfx1150"
            "-DCMAKE_HIP_ARCHITECTURES=gfx1150"
          ];
          preConfigure = null;
          npmDepsHash = "sha256-a17M+L3nLdRnN6WMB6imPFmwqG2g8uv+gwN0XTAUrf8=";
          npmRoot = "tools/ui";
          nativeBuildInputs = builtins.filter (p: (p.pname or "") != "npm-config-hook")
            (old.nativeBuildInputs or [ ]);
        });

        # rocm-smi for VRAM/GPU-util evidence (nixpkgs only exposes it under
        # rocmPackages.*, not as a top-level package).
        inherit (pkgs) llama-cpp-rocm;
        rocm-smi = pkgs.rocmPackages.rocm-smi;
      });
    };
}
