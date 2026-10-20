"""Assert the pinned Core structure before replacing argv0 relocation."""

from pathlib import Path

path = Path("src/common/core.cpp")
text = path.read_text()
include = '#include "strlib.hpp"'
assert text.count(include) == 1
text = text.replace(include, include + '\n#include "runtime-root.hpp"')
start = "int32 Core::start( int32 argc, char **argv ){"
assert text.count(start) == 1
cli = r'''
    // runtime_root_offline_cli: before status, malloc, SQL, socket, timer, config, role init.
    SERVER_NAME = runtime_root::server_basename(argv[0]);
    if (argc == 2 && (!strcmp(argv[1], "--help") || !strcmp(argv[1], "--version"))) {
        printf("rAthena pinned e985006171d2eb320ee512a653f4c83aea3d81b6 MAIN/pre-re PACKETVER=20180704\n");
        printf("Offline only: --help | --version | --check-runtime-root <literal-absolute-private-directory>.\n");
        printf("All native startup remains blocked; directory diagnostics are not world validation.\n");
        return EXIT_SUCCESS;
    }
    if (argc == 3 && !strcmp(argv[1], "--check-runtime-root")) {
        return runtime_root::diagnostic(argv[2], SERVER_NAME);
    }
    fprintf(stderr, "rAthena: runtime-start executor is blocked.\n");
    return 78; // unconditional runtime-start refusal
'''
text = text.replace(start, start + cli)
first = text.index("\t{// initialize program arguments", text.index(start))
last = text.index("\n\tmalloc_init();", first)
old = text[first:last]
assert "chdir(pwd)" in old and "SERVER_NAME = ++p1;" in old
text = text[:first] + "\t// Explicit root selection belongs to bind_runtime_root; never relocate via argv[0].\n" + text[last:]
assert "chdir(pwd)" not in text
path.write_text(text)
Path("core-start.cpp").write_text(text)
with Path("src/custom/defines_post.hpp").open("a") as custom:
    custom.write("\n#undef PACKET_OBFUSCATION\n#undef PACKET_OBFUSCATION_WARN\n")
