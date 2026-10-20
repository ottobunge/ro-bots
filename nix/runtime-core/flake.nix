{
  description = "Pinned rAthena native runtime-root diagnostic; all startup blocked";
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
      runtimeCore = pkgs.stdenv.mkDerivation {
        pname = "rathena-runtime-core-offline";
        version = "20180704-${builtins.substring 0 12 revision}";
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
        '';
        postConfigure = ''
          python3 ${./profile-evidence.py}
        '';
        installPhase = ''
          runHook preInstall
          mkdir -p "$out/libexec/rathena" "$out/share/rathena-runtime-core"
          install -m755 login-server char-server map-server "$out/libexec/rathena/"
          install -m644 LICENSE core-start.cpp src/common/runtime-root.hpp profile-oracle.cpp profiles.json *-cppflags.txt *-compile-recipe.txt "$out/share/rathena-runtime-core/"
          install -m644 ${./apply-runtime-root.py} ${./profile-evidence.py} "$out/share/rathena-runtime-core/"
          cat > "$out/share/rathena-runtime-core/package.json" <<'EOF'
          {"revision":"${revision}","packetver":20180704,"client_family":"MAIN","ruleset":"pre-re","startup_blocked":true,"diagnostic_scope":"filesystem-root-only"}
          EOF
          runHook postInstall
        '';
        meta = {
          description = "Offline native filesystem-root diagnostic; not a runnable world";
          license = pkgs.lib.licenses.gpl3Plus;
          platforms = [ system ];
        };
      };
    in {
      packages.${system} = {
        default = runtimeCore;
        runtime-core = runtimeCore;
      };
      devShells.${system}.default = pkgs.mkShell {
        packages = [ pkgs.python3 pkgs.python3Packages.pytest pkgs.ruff pkgs.black pkgs.strace ];
      };
    };
}
