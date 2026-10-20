"""Compile profile oracles using each generated native object recipe's flags."""

import json
import shlex
import subprocess
from pathlib import Path

oracle = r'''
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
'''
Path("profile-oracle.cpp").write_text(oracle)
profiles = {}
for role in ("common", "login", "char", "map"):
    makefile = Path(f"src/{role}/Makefile").read_text()
    line = next(line for line in makefile.splitlines() if "-DPACKETVER=" in line and "-c " in line)
    tokens = shlex.split(line.strip().lstrip("@"))
    flags = [token for token in tokens if token.startswith(("-D", "-f", "-std="))]
    assert "-DPACKETVER=20180704" in flags and "-DPRERE" in flags
    Path(f"{role}-cppflags.txt").write_text(" ".join(flags) + "\n")
    Path(f"{role}-compile-recipe.txt").write_text(line + "\n")
    subprocess.run([tokens[0], *flags, "-I.", "-Isrc", "profile-oracle.cpp", "-o", "profile-oracle"], check=True)
    profiles[role] = json.loads(subprocess.check_output(["./profile-oracle"]))
Path("profiles.json").write_text(json.dumps(profiles, indent=2) + "\n")
