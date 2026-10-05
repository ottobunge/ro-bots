{
  # Spike 005-gpu-clef (ro-bots): CUDA llama.cpp (Clef-capable a7fb71f) for 2x Quadro RTX 8000.
  #
  # Usage (on heavengraph, NixOS):
  #   nix build .#llama-cpp-clef-cuda --out-link ./result
  #   ./result/bin/llama-server -m <model>.gguf -ngl 99 --port 8091 --host 0.0.0.0 ...
  #
  # Why this shape:
  #  - nixpkgs llama-cpp is 0.5.0 (2026-09-23), predating the Clef merge
  #    (PR #29831, 2026-10-03): no tools/server/server-decision.cpp, no
  #    /v1/systemone. So we reuse nixpkgs' packaging with the vendored
  #    Clef-capable source (same pin as spike 001).
  #  - cudaSupport turns on the GGML CUDA backend; cudaPackages supplies nvcc.
  #    RTX 8000 is Turing => CMAKE_CUDA_ARCHITECTURES=75.
  #  - WebUI is disabled (same npm pin problem as spike 001; we run --no-webui).
  inputs.nixpkgs.url = "nixpkgs";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" ];
      # CUDA EULA is unfree; allow it. Extend via config scoped to a fresh
      # nixpkgs eval rather than an overlay (overlays break stage.nix config attrs).
      allowCuda = pkgs: import pkgs.path { config = { allowUnfree = true; }; localSystem = pkgs.stdenv.hostPlatform.system; };
      forAll = f: nixpkgs.lib.genAttrs systems (system: f (allowCuda nixpkgs.legacyPackages.${system}));
    in
    {
      devShells = forAll (pkgs: {
        default = pkgs.mkShell {
          packages = with pkgs; [
            cmake
            ninja
            gcc
            pkg-config
            python3
            git
            curl
            nvtopPackages.full
          ];
          shellHook = ''
            echo "ro-bots GPU dev shell: cmake+ninja+gcc ready."
            echo "  build:   nix build .#llama-cpp-clef-cuda --out-link ./result"
            echo "  bench:   python3 bench.py --url http://localhost:8091"
          '';
        };
      });

      packages = forAll (pkgs: {
        # nixpkgs' llama-cpp packaging with CUDA + Clef-capable source (a7fb71f).
        llama-cpp-clef-cuda =
          (pkgs.llama-cpp.override {
            cudaSupport = true;
            cudaPackages = pkgs.cudaPackages;
          }).overrideAttrs (old: {
            pname = "llama-cpp-clef-cuda";
            version = "0.5.0-clef-a7fb71f-cuda";
            src = pkgs.lib.cleanSource ./llama.cpp;
            # master's webui package-lock differs from 0.5.0's pinned npmDepsHash;
            # we run with --no-webui so drop the npm ui build entirely.
            cmakeFlags = (old.cmakeFlags or []) ++ [
              "-DCMAKE_CUDA_ARCHITECTURES=75"
              "-DLLAMA_BUILD_WEBUI=OFF"
              "-DLLAMA_BUILD_UI=OFF"
              "-DGGML_CUDA_F16=ON"
              "-DGGML_CUDA_FORCE_MMQ=ON"
            ];
            preConfigure = null;
            npmDepsHash = "sha256-a17M+L3nLdRnN6WMB6imPFmwqG2g8uv+gwN0XTAUrf8=";
            npmRoot = "tools/ui";
            nativeBuildInputs = builtins.filter (p: (p.pname or "") != "npm-config-hook")
              (old.nativeBuildInputs or []);
          });

        # Non-CUDA fallback (CPU-only) in case CUDA eval breaks on this nixpkgs.
        llama-cpp-clef = (pkgs.llama-cpp.override { }).overrideAttrs (old: {
          pname = "llama-cpp-clef";
          version = "0.5.0-clef-a7fb71f";
          src = pkgs.lib.cleanSource ./llama.cpp;
          cmakeFlags = (old.cmakeFlags or []) ++ [
            "-DLLAMA_BUILD_WEBUI=OFF"
            "-DLLAMA_BUILD_UI=OFF"
          ];
          preConfigure = null;
          npmDepsHash = "sha256-a17M+L3nLdRnN6WMB6imPFmwqG2g8uv+gwN0XTAUrf8=";
          npmRoot = "tools/ui";
          nativeBuildInputs = builtins.filter (p: (p.pname or "") != "npm-config-hook")
            (old.nativeBuildInputs or []);
        });
      });
    };
}
