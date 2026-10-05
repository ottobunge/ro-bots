{
  description = "ro-bots: Clef-driven bot players for a private rAthena server";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          go-task          # task runner: `task quality`, `task format`, ...
          uv               # python env + dep management (uv sync, uv run, uv lock)
          python314
          ruff             # lint + format + import sorting + duplicate-code detection
          mypy             # static type checking
        ];
        shellHook = ''
          echo "ro-bots dev shell — try: task --list"
        '';
      };
    };
}
