"""Observable selected sender AST identities; no semantic or native admission."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def walk(node):
    yield node
    for child in node.get('inner', []):
        yield from walk(child)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('sender', choices=['clif_emotion', 'clif_name', 'clif_sitting'])
    parser.add_argument('--profile', default='20180704')
    args = parser.parse_args()
    if args.profile != '20180704':
        parser.error('unsupported profile: only immutable MAIN20180704/pre-re evidence')
    manifest = json.loads((ROOT / 'commands.json').read_text())
    label = 'clang-original-' + args.sender.removeprefix('clif_')
    step = next(s for s in manifest['steps'] if s['name'] == label)
    if step['exit'] != 0:
        parser.error('full translation unit frontend failed: no admitted AST')
    path = ROOT / (label + '.stdout')
    if not path.is_file():
        parser.error('missing AST: rerun recorded full-TU compiler command')
    raw = path.read_text()
    decoder = json.JSONDecoder()
    roots = []
    while raw.strip():
        node, end = decoder.raw_decode(raw.lstrip())
        roots.append(node)
        raw = raw.lstrip()[end:]
    fn = next(n for n in roots if n.get('kind') == 'FunctionDecl' and n.get('name') == args.sender and any(c['kind'] == 'CompoundStmt' for c in n.get('inner', [])))
    nodes = list(walk(fn))
    result = {
        'function': {k: fn[k] for k in ('id', 'name', 'mangledName', 'loc', 'range', 'type') if k in fn},
        'declarations': [{k: n[k] for k in ('id', 'kind', 'name', 'type', 'loc', 'range') if k in n} for n in nodes if n['kind'] in ('VarDecl', 'ParmVarDecl')],
        'references': [n['referencedDecl'] for n in nodes if n['kind'] == 'DeclRefExpr'],
        'sizeof_nodes': [n for n in nodes if n['kind'] == 'UnaryExprOrTypeTraitExpr' and n.get('name') == 'sizeof'],
        'send_calls': [n for n in nodes if n['kind'] == 'CallExpr' and any(c.get('referencedDecl', {}).get('name') == 'clif_send' for c in walk(n.get('inner', [{}])[0]))],
        'ast_path': str(path), 'ast_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'frontend': 'Clang 21.1.8; independently preprocessed original full TU',
        'native_admission': False, 'semantic_admission': False,
        'exact_installed_profile_verified': False,
        'observed_profile': {'family': 'MAIN', 'packetver': 20180704, 'ruleset': 'pre-re', 'obfuscation': True},
        'profile_blocker': 'Unmodified source defines PACKET_OBFUSCATION; installed apply-runtime-root.py appends undef directives to src/custom/defines_post.hpp. No source edits or unreviewed forced headers were used.',
        'limitations': ['AST IDs are local to this invocation.', 'No CFG, alias, mutation or interprocedural proof.'],
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
