{
  description = "Small offline prepared-world import helper; no engine or SQL execution";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      helper = pkgs.runCommand "world-volume-import" {} ''
        mkdir -p "$out/libexec"
        install -m644 ${./import-stage.py} "$out/libexec/import-stage.py"
      '';
      image = pkgs.dockerTools.buildLayeredImage {
        name = "ro-bots-world-init";
        tag = "local";
        created = "1970-01-01T00:00:01Z";
        contents = [ pkgs.python3 helper ];
        config = {
          User = "0:0";
          Entrypoint = [ "${pkgs.python3}/bin/python3" "${helper}/libexec/import-stage.py" ];
          Cmd = [ "--source" "/prepared" "--destination" "/world"
            "--runtime-uid" "10000" "--runtime-gid" "10000"
            "--mysql-uid" "999" "--mysql-gid" "999" ];
        };
      };
    in {
      packages.${system} = { default = image; docker-image = image; inherit helper; };
      devShells.${system}.default = pkgs.mkShell {
        packages = [
          (pkgs.python3.withPackages (ps: [ ps.pytest ps.httpx ps.pyyaml ]))
          pkgs.black pkgs.ruff pkgs.mypy
        ];
      };
    };
}
