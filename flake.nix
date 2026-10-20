{
  description = "ro-bots: Clef-driven bot players for a private rAthena server";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      rathenaRevision = "e985006171d2eb320ee512a653f4c83aea3d81b6";
      rathenaSource = pkgs.fetchFromGitHub {
        owner = "rathena";
        repo = "rathena";
        rev = rathenaRevision;
        hash = "sha256-ppi6wPYDqwXh+XR39ufl0SDS6gYfdKyHtQ9tU9rgrNI=";
      };
      rathenaValidator = pkgs.writeText "rathena-private-config-validator.py" ''
        import argparse
        import json
        import os
        import re
        import stat
        import sys

        def refuse(message, status=2):
            sys.stderr.write(message + "\n")
            raise SystemExit(status)

        class Parser(argparse.ArgumentParser):
            def error(self, message):
                refuse("unsupported package command or arguments")

        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate field")
                result[key] = value
            return result

        def load_private(path):
            if not os.path.isabs(path):
                raise ValueError("absolute file required")
            parts = path.split('/')[1:]
            if not parts or any(p in ("", ".", "..") for p in parts):
                raise ValueError("literal path required")
            fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
            try:
                for part in parts[:-1]:
                    next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.close(fd)
                    fd = next_fd
                leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                try:
                    info = os.fstat(leaf)
                    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
                        raise ValueError("private regular file required")
                    if stat.S_IMODE(info.st_mode) not in (0o400, 0o600) or info.st_size > 8192:
                        raise ValueError("private bounded file required")
                    raw = os.read(leaf, 8193)
                    if len(raw) > 8192:
                        raise ValueError("file too large")
                    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object)
                finally:
                    os.close(leaf)
            finally:
                os.close(fd)

        def validate(data):
            fields = {'server_mode', 'db_host', 'db_port', 'db_name', 'db_user',
                      'db_password', 'inter_user', 'inter_password'}
            if not isinstance(data, dict) or set(data) != fields:
                raise ValueError("unsupported schema")
            if data['server_mode'] != 'MAIN-pre-re-20180704':
                raise ValueError("unsupported profile")
            if type(data['db_port']) is not int or not 1 <= data['db_port'] <= 65535:
                raise ValueError("explicit TCP port required")
            host = data['db_host']
            if not isinstance(host, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}', host):
                raise ValueError("explicit hostname required")
            if host.lower() == 'localhost' or host.startswith('127.'):
                raise ValueError("native SQL fallback forbidden")
            for field in ('db_name', 'db_user', 'inter_user'):
                value = data[field]
                if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_]{1,23}', value):
                    raise ValueError("unsafe configuration field")
            for field in ('db_password', 'inter_password'):
                value = data[field]
                if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_!@$%^&*+=.,?-]{1,32}', value):
                    raise ValueError("unsafe configuration field")

        parser = Parser(description='Offline rAthena package; no world launch authority.')
        parser.add_argument('--version', action='version', version='rAthena ${rathenaRevision} MAIN/pre-re 20180704')
        parser.add_argument('command', choices=('validate', 'launch'))
        parser.add_argument('role', nargs='?', choices=('login', 'char', 'map'))
        parser.add_argument('--secret-file')
        args = parser.parse_args()
        if not args.secret_file:
            refuse('explicit private secret file is required')
        try:
            validate(load_private(args.secret_file))
        except (OSError, ValueError, UnicodeError):
            refuse('private configuration rejected')
        if args.command == 'launch':
            refuse('isolated-world launch executor is blocked', 78)
        sys.stdout.write('Private configuration valid; does not authorize launch.\n')
      '';
      rathenaServer = pkgs.stdenv.mkDerivation {
        pname = "rathena-server";
        version = "20180704-${builtins.substring 0 12 rathenaRevision}";
        src = rathenaSource;
        nativeBuildInputs = [ pkgs.python3 ];
        buildInputs = [ pkgs.zlib pkgs.pcre pkgs.libmysqlclient ];
        configureFlags = [
          "--enable-packetver=20180704"
          "--enable-prere=yes"
          "--disable-lto"
          "--with-mysql=${pkgs.libmysqlclient.dev}/bin/mysql_config"
          "--with-pcre"
        ];
        enableParallelBuilding = true;
        makeFlags = [ "login" "char" "map" ];
        postPatch = ''
          # The existing fixture's disabled runtime obfuscation is explicit here.
          cat >> src/custom/defines_post.hpp <<'EOF'
          #undef PACKET_OBFUSCATION
          #undef PACKET_OBFUSCATION_WARN
          EOF
          python3 - <<'PY'
          from pathlib import Path
          p = Path('src/common/core.cpp')
          text = p.read_text()
          marker = '\tthis->set_status( e_core_status::CORE_INITIALIZING );'
          assert text.count(marker) == 1
          early = r"""
          // rathena_package_offline_cli: before SQL, socket, timer or config initialization.
          if (argc == 2 && (!strcmp(argv[1], "--help") || !strcmp(argv[1], "--version"))) {
              printf("rAthena pinned ${rathenaRevision} MAIN/pre-re PACKETVER=20180704\n");
              printf("Offline package: --help | --version; isolated-world launch executor is blocked.\n");
              return EXIT_SUCCESS;
          }
          fprintf(stderr, "rAthena: isolated-world launch executor is blocked.\n");
          return 78;
          """
          p.write_text(text.replace(marker, early + '\n' + marker))
          Path('core-start.cpp').write_text(p.read_text())
          PY
        '';
        postConfigure = ''
          python3 - <<'PY'
          from pathlib import Path
          import re, shlex, subprocess
          makefile = Path('src/map/Makefile').read_text()
          line = next(l for l in makefile.splitlines() if '-DPACKETVER=' in l and '-c ' in l)
          tokens = shlex.split(line.strip().lstrip('@'))
          flags = [t for t in tokens if t.startswith('-D') or t.startswith('-f') or t.startswith('-std=')]
          assert '-DPACKETVER=20180704' in flags and '-DPRERE' in flags
          Path('map-cppflags.txt').write_text(' '.join(flags) + '\n')
          oracle = r"""
          #include "src/common/mmo.hpp"
          #include <cstdio>
          static_assert(PACKETVER == 20180704);
          static_assert(PACKETVER_MAIN_NUM == 20180704);
          static_assert(PACKETVER_SUPPORTS_PINCODE);
          #if defined(RENEWAL) || defined(PACKETVER_RE) || defined(PACKETVER_ZERO) || defined(PACKET_OBFUSCATION)
          #error incorrect compiled profile
          #endif
          int main() {
            printf("{\"packetver\":%d,\"main\":%d,\"renewal\":false,\"re\":false,\"zero\":false,\"obfuscation\":false,\"pincode\":%s}\n", PACKETVER, PACKETVER_MAIN_NUM, PACKETVER_SUPPORTS_PINCODE ? "true" : "false");
          }
          """
          Path('profile-oracle.cpp').write_text(oracle)
          subprocess.run([tokens[0], *flags, '-I.', '-Isrc', 'profile-oracle.cpp', '-o', 'profile-oracle'], check=True)
          Path('profile.json').write_bytes(subprocess.check_output(['./profile-oracle']))
          PY
        '';
        installPhase = ''
          runHook preInstall
          mkdir -p "$out/libexec/rathena" "$out/share/rathena/db"
          install -m755 login-server char-server map-server "$out/libexec/rathena/"
          cp -r db/. "$out/share/rathena/db/"
          rm -rf "$out/share/rathena/db/re" "$out/share/rathena/db/import" "$out/share/rathena/db/import-tmpl"
          install -m644 LICENSE "$out/share/rathena/LICENSE"
          mkdir -p "$out/share/rathena/build-evidence"
          install -m644 core-start.cpp profile.json profile-oracle.cpp map-cppflags.txt "$out/share/rathena/build-evidence/"
          mkdir -p "$out/bin" "$out/share/rathena/conf"
          cp -r conf/battle conf/msg_conf "$out/share/rathena/conf/"
          rm -rf "$out/share/rathena/conf/msg_conf/import" "$out/share/rathena/conf/msg_conf/import-tmpl"
          cat > "$out/bin/rathena-package" <<'EOF'
          #!${pkgs.runtimeShell}
          exec ${pkgs.python3}/bin/python3 -B ${rathenaValidator} "$@"
          EOF
          chmod 755 "$out/bin/rathena-package"
          export out
          python3 - <<'PY'
          import json, os
          from pathlib import Path
          root = Path(os.environ['out']) / 'share/rathena'
          assets = sorted(str(p.relative_to(root)) for p in root.rglob('*')
                          if p.is_file() and str(p.relative_to(root)).startswith(('db/', 'conf/')))
          Path(root / 'asset-manifest.json').write_text(json.dumps(assets, indent=2) + '\n')
          PY
          cat > "$out/share/rathena/package.json" <<'EOF'
          {"revision":"${rathenaRevision}","packetver":20180704,"client_family":"MAIN","ruleset":"pre-re"}
          EOF
          runHook postInstall
        '';
        meta = {
          description = "Pinned MAIN/pre-Renewal rAthena binaries; offline packaging slice";
          license = pkgs.lib.licenses.gpl3Plus;
          platforms = [ system ];
        };
      };
    in
    {
      packages.${system} = {
        rathena-server = rathenaServer;
        rathena-image = pkgs.dockerTools.buildLayeredImage {
        name = "ro-bots-rathena-offline";
        tag = "20180704-${builtins.substring 0 12 rathenaRevision}";
        created = "1970-01-01T00:00:01Z";
        contents = [ rathenaServer ];
        maxLayers = 32;
        config = {
          Entrypoint = [ "${rathenaServer}/bin/rathena-package" ];
          Cmd = [ "--help" ];
          User = "10001:10001";
          WorkingDir = "/";
          Env = [ "PYTHONDONTWRITEBYTECODE=1" ];
          Labels = {
            "org.opencontainers.image.revision" = rathenaRevision;
            "org.opencontainers.image.description" = "Offline MAIN/pre-re20180704 package; launch executor blocked";
          };
        };
        };
      };
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          go-task          # task runner: `task quality`, `task format`, ...
          uv               # python env + dep management (uv sync, uv run, uv lock)
          python314
          ruff             # lint + format + import sorting + duplicate-code detection
          mypy             # static type checking
          cargo rustc rustfmt clippy cargo-audit cargo-machete
          pkg-config openssl
        ];
        shellHook = ''
          echo "ro-bots dev shell — try: task --list"
        '';
      };
    };
}
