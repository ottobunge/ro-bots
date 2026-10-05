{
  # Spike 001-clef-local (ro-bots): local Clef-Flash decision model + Qwen chat.
  #
  # Usage:
  #   nix develop .#          # shell with cmake/ninja/gcc/python3 to build & bench
  #   nix build .#llama-cpp-clef   # reproducible llama.cpp (Clef support, master a7fb71f) -> ./result
  #
  # Why a source build? nixpkgs llama-cpp is 0.5.0 (tag v0.5.0, 2026-09-23),
  # which predates the Clef merge (PR #29831, 2026-10-03): no tools/server/
  # server-decision.cpp, no /v1/systemone. nixpkgs will pick Clef up in a
  # later release; until then this flake builds ggml-org/llama.cpp master.
  inputs.nixpkgs.url = "nixpkgs";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin" ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forAll (pkgs: {
        default = pkgs.mkShell {
          packages = with pkgs; [
            gcc           # C/C++ toolchain (no system cc on NixOS)
            cmake
            ninja
            pkg-config
            python3       # stdlib only; bench.py needs nothing else
            git
            curl
            htop
          ];
          shellHook = ''
            echo "ro-bots dev shell: cmake+ninja+gcc ready."
            echo "  build llama.cpp:  cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON && cmake --build build -j\$(nproc)"
            echo "  or:               nix build .#llama-cpp-clef"
            echo "  bench:            python3 bench.py"
          '';
        };
      });

      packages = forAll (pkgs: {
        # Reuse nixpkgs' llama-cpp packaging (static BLAS backend, proven 10x
        # faster than a plain ggml-cpu build on this host) with the Clef-capable
        # master source (a7fb71f). nixpkgs 0.5.0 predates the Clef merge.
        llama-cpp-clef = (pkgs.llama-cpp.override {
          # keep nixpkgs' own feature switches; add nothing CPU-arch specific
        }).overrideAttrs (old: {
          pname = "llama-cpp-clef";
          version = "0.5.0-clef-a7fb71f";
          src = pkgs.lib.cleanSource ./llama.cpp;
          # nixpkgs' derivation derives the version from the tag; keep theirs.
        });
      });
    };
}
