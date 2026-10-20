"""Fail closed on pinned-source drift; preserve the original Core startup tail."""

import hashlib
from pathlib import Path

path = Path("src/common/core.cpp")
raw = path.read_bytes()
assert hashlib.sha256(raw).hexdigest() == "e64fc8fc0c6bb1a025ebf6ac9c80cf026dfdb1a386eb3d1d7c678d4ca782a117", "pinned Core source drift"
text = raw.decode()
include = '#include "strlib.hpp"'
start = "int32 Core::start( int32 argc, char **argv ){"
for anchor in (include, start, "\t{// initialize program arguments", "\tmalloc_init();", "\tSql_Init();", "\ttimer_init();", "\tsocket_init();", "this->initialize( argc, argv )"):
    assert text.count(anchor) == 1, f"unexpected Core anchor: {anchor}"
original_tail = text[text.index("\tmalloc_init();"):]
first = text.index("\t{// initialize program arguments", text.index(start))
last = text.index("\n\tmalloc_init();", first)
old = text[first:last]
assert old.count("chdir(pwd)") == 1 and old.count("SERVER_NAME = ++p1;") == 1
text = text[:first] + "\t// Explicit fd-bound runtime root; never relocate via argv[0].\n" + text[last:]
text = text.replace(include, include + '\n#include "runtime-root.hpp"')
cli = r'''
    // Before Core status, malloc, SQL, timers, sockets, config or role initialization.
    SERVER_NAME = runtime_root::server_basename(argv[0]);
    const int runtime_result = runtime_root::prepare(argc, argv, SERVER_NAME);
    if (runtime_result != -1) return runtime_result;
'''
text = text.replace(start, start + cli)
assert "chdir(pwd)" not in text
assert text[text.index("\tmalloc_init();"):] == original_tail
path.write_text(text)
Path("core-start.cpp").write_text(text)
with Path("src/custom/defines_post.hpp").open("a") as custom:
    custom.write("\n#undef PACKET_OBFUSCATION\n#undef PACKET_OBFUSCATION_WARN\n")
