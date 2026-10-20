{
  description = "Pinned MariaDB software for future isolated rAthena worlds; offline defaults";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  outputs = { nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      database = pkgs.mariadb;
      created = "1970-01-01T00:00:01Z";
      identity = pkgs.runCommand "rathena-db-public-identity" {} ''
        mkdir -p "$out/etc"
        printf 'db:x:10001:10001:Offline DB software:/:/bin/false\n' > "$out/etc/passwd"
        printf 'db:x:10001:\n' > "$out/etc/group"
      '';
    in {
      packages.${system} = {
        rathena-db = database;
        rathena-db-image = pkgs.dockerTools.buildLayeredImage {
          name = "ro-bots-rathena-db-offline";
          tag = "${database.version}-${builtins.substring 0 12 nixpkgs.rev}";
          inherit created;
          contents = [ database pkgs.coreutils pkgs.gnused pkgs.gnugrep pkgs.gawk identity ];
          maxLayers = 32;
          config = {
            Entrypoint = [ "${database}/bin/mariadbd" ];
            Cmd = [ "--no-defaults" "--version" ];
            User = "10001:10001";
            WorkingDir = "/";
            Env = [ "HOME=/nonexistent" "PATH=${pkgs.lib.makeBinPath [ database pkgs.coreutils pkgs.gnused pkgs.gnugrep pkgs.gawk ]}" ];
            Labels = {
              "org.opencontainers.image.version" = database.version;
              "org.opencontainers.image.revision" = nixpkgs.rev;
              "org.opencontainers.image.created" = created;
              "org.opencontainers.image.description" = "Public DB software only; no initialized world or launch authority";
              "org.ro-bots.nixpkgs.revision" = nixpkgs.rev;
              "org.ro-bots.nixpkgs.nar-hash" = nixpkgs.narHash;
              "org.ro-bots.image.format" = "docker-archive";
              "org.ro-bots.authority" = "offline-artifact-only";
            };
          };
        };
      };
    };
}
