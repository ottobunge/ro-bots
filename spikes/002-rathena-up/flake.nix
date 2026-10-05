{
  description = "Spike 002-rathena-up: fully self-contained dev shell to build and run a private rAthena RO server (local MariaDB datadir, localhost only) plus clientless bot tests. nix develop + ./start.sh reproduces everything from a clean checkout.";

  inputs = {
    # Pinned nixpkgs for reproducibility
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { system = system; };
      # mariadb split package: .out has the server+client binaries, .dev has mysql.h / mariadb_config
      mariadbDev = pkgs.libmysqlclient.dev; # mysql client headers (mariadb-connector-c)
      mariadbOut = pkgs.libmysqlclient;     # libmariadb.so / libmysqlclient.so
      mariadbServer = pkgs.mariadb;         # mariadbd/mysqld + mysql/mariadb clients + mysql_install_db
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          # build toolchain
          gcc
          gnumake
          cmake
          pkg-config
          git

          # rAthena build deps
          zlib
          pcre          # libpcre (pcre.h) — rAthena's configure requires pcre
          mariadbServer # mariadbd (mysqld), mariadb/mysql client, mysqld_safe
          mariadbDev    # mysql_config + mysql.h (libmysqlclient.dev = mariadb-connector-c dev)
          mariadbOut    # libmysqlclient runtime lib

          # runtime helpers
          python3
          nettools      # ss
          lsof
          procps
        ];

        # mysql_config ships in the .dev output; rAthena's ./configure calls it.
        # MariaDB server binaries need their basedir to find language files/plugins.
        MYSQL_BASEDIR = "${mariadbServer}";
        MYSQL_DEV = "${mariadbDev}";
        MYSQL_OUT = "${mariadbOut}";
        shellHook = ''
          export LC_ALL=C.UTF-8
          echo "[ro-bots spike shell] gcc=$(gcc -dumpversion), mariadb=$(mariadb --version | cut -d' ' -f6)"
          echo "  mysqld: $(command -v mariadbd || command -v mysqld)"
          echo "  mysql_config: $(command -v mysql_config)"
          echo "  usage: ./start.sh (boots mysqld + login/char/map servers) — see README.md"
        '';
      };
    };
}
