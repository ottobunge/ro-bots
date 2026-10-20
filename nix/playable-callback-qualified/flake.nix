{
  description = "Pinned rAthena with explicit runtime selection; separate from accepted offline artifacts";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      revision = "e985006171d2eb320ee512a653f4c83aea3d81b6";
      source = pkgs.fetchFromGitHub {
        owner = "rathena";
        repo = "rathena";
        rev = revision;
        hash = "sha256-ppi6wPYDqwXh+XR39ufl0SDS6gYfdKyHtQ9tU9rgrNI=";
      };
      playable = pkgs.stdenv.mkDerivation {
        pname = "rathena-playable-callback-qualified";
        version = "20180704-${builtins.substring 0 12 revision}-callback-qualified";
        src = source;
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
          install -m644 ${./runtime-root.hpp} src/common/runtime-root.hpp
          python3 ${./apply-runtime-root.py}
          python3 ${./qualify-callback.py} "$PWD"
        '';
        postConfigure = ''
          python3 ${./profile-evidence.py}
          python3 ${./source-evidence.py}
        '';
        installPhase = ''
          runHook preInstall
          mkdir -p "$out/libexec/rathena" "$out/share/rathena-playable-callback-qualified"
          install -m755 login-server char-server map-server "$out/libexec/rathena/"
          install -m644 configured-source.json LICENSE core-start.cpp src/common/runtime-root.hpp profile-oracle.cpp profiles.json *-cppflags.txt *-compile-recipe.txt "$out/share/rathena-playable-callback-qualified/"
          install -m644 ${./apply-runtime-root.py} "$out/share/rathena-playable-callback-qualified/apply-runtime-root.py"
          install -m644 ${./profile-evidence.py} "$out/share/rathena-playable-callback-qualified/profile-evidence.py"
          install -m644 src/map/clif.cpp "$out/share/rathena-playable-callback-qualified/qualified-clif.cpp"
          install -m644 ${./qualify-callback.py} "$out/share/rathena-playable-callback-qualified/qualify-callback.py"
          install -m644 ${./source-evidence.py} "$out/share/rathena-playable-callback-qualified/source-evidence.py"
          cat > "$out/share/rathena-playable-callback-qualified/package.json" <<'EOF'
          {"variant":"callback-qualified","pointer_corrections":4,"qualified_clif_sha256":"ace16f15be3b60f730522d620b73a68a9f2cc384016aadce9c985888aea9a1ac","revision":"${revision}","packetver":20180704,"client_family":"MAIN","ruleset":"pre-re","runtime_selection_required":true,"diagnostic_scope":"filesystem-root-only","native_gameplay_verified":false,"runtime_assets_bundled":false}
          EOF
          runHook postInstall
        '';
        meta = {
          description = "Real native startup behind explicit runtime selection; prepared assets and SQL required";
          license = pkgs.lib.licenses.gpl3Plus;
          platforms = [ system ];
        };
      };
      image = pkgs.dockerTools.buildLayeredImage {
        name = "rathena-playable-callback-qualified";
        tag = "20180704-${builtins.substring 0 12 revision}-callback-qualified";
        created = "1970-01-01T00:00:01Z";
        contents = [ playable ];
        config = {
          User = "10000:10000";
          WorkingDir = "/world";
          Volumes = { "/world" = {}; };
          Entrypoint = [ "${playable}/libexec/rathena/login-server" ];
          Cmd = [];
          Labels = {
            "org.opencontainers.image.revision" = revision;
            "org.opencontainers.image.licenses" = "GPL-3.0-or-later";
            "org.rathena.profile" = "MAIN-pre-re-20180704";
            "org.rathena.runtime-root" = "explicit-same-uid-0700";
          };
        };
      };
    in {
      packages.${system} = {
        default = playable;
        playable-rathena = playable;
        docker-image = image;
      };
      devShells.${system}.default = pkgs.mkShell {
        packages = [ pkgs.python3 pkgs.python3Packages.pytest pkgs.ruff pkgs.black pkgs.strace ];
      };
    };
}
