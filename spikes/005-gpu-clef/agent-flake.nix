{
  # framework-agents: CUDA llama.cpp serving (Clef decision models) on NixOS
  # (Heavengraph, 2x Quadro RTX 8000 / Turing sm_75).
  #
  # Usage:
  #   nix build .#llama-cpp-clef-cuda --out-link ./result
  #   nix run .#serve          # or: bash serve.sh
  #
  # Why a source build: nixpkgs llama-cpp 0.5.0 (2026-09-23) predates the Clef
  # merge (PR #29831, 2026-10-03) — no tools/server/server-decision.cpp, no
  # POST /v1/systemone. This flake reuses nixpkgs' packaging with the pinned
  # Clef-capable source (a7fb71f, same as spike 001) and CUDA enabled.
  # CUDA EULA is unfree, hence config.allowUnfree on the nixpkgs instance.
  inputs.nixpkgs.url = "nixpkgs";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      # Fresh nixpkgs instance with allowUnfree (a plain overlay breaks stage.nix
      # config attrs like attrPathsDisallowedForInternalUse).
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfree = true; # CUDA EULA (nvcc, libcublas, ...)
      };

      llama-cpp-clef-cuda = (pkgs.llama-cpp.override {
        cudaSupport = true;
        cudaPackages = pkgs.cudaPackages;
      }).overrideAttrs (old: {
        pname = "llama-cpp-clef-cuda";
        version = "0.5.0-clef-a7fb71f-cuda";
        src = pkgs.lib.cleanSource ./llama.cpp;
        # WebUI dropped (npm pin mismatch on master; we run --no-webui).
        cmakeFlags = (old.cmakeFlags or []) ++ [
          "-DCMAKE_CUDA_ARCHITECTURES=75" # Quadro RTX 8000 = Turing sm_75
          "-DLLAMA_BUILD_WEBUI=OFF"
          "-DLLAMA_BUILD_UI=OFF"
        ];
        preConfigure = null;
        npmDepsHash = "sha256-a17M+L3nLdRnN6WMB6imPFmwqG2g8uv+gwN0XTAUrf8=";
        npmRoot = "tools/ui";
        nativeBuildInputs = builtins.filter (p: (p.pname or "") != "npm-config-hook")
          (old.nativeBuildInputs or []);
      });

      serve = pkgs.writeShellScriptBin "serve" ''
        exec bash ${./serve.sh}
      '';
    in
    {
      packages.${system} = {
        inherit llama-cpp-clef-cuda;
        default = llama-cpp-clef-cuda;
      };

      apps.${system} = {
        serve = {
          type = "app";
          program = "${serve}/bin/serve";
        };
      };

      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [ cmake ninja gcc pkg-config python3 git curl nvtopPackages.full ];
        shellHook = ''
          echo "framework-agents GPU dev shell."
          echo "  build:  nix build .#llama-cpp-clef-cuda --out-link ./result"
          echo "  serve:  nix run .#serve"
        '';
      };
    };
}
