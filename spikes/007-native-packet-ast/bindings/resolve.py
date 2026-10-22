"""Restricted offline fixture recognizer; no production sender authority."""

import argparse
import hashlib
import json
import pathlib
import subprocess

CLANG = "/nix/store/2msw5nclhpsm80z65dqmjiv8kkras989-clang-wrapper-21.1.8/bin/clang++"
OPTIONS = [
    "-std=c++17",
    "-Wno-unused-command-line-argument",
    "-fsyntax-only",
    "-Xclang",
    "-ast-dump=json",
]
CASTS = {
    "LValueToRValue",
    "IntegralCast",
    "FunctionToPointerDecay",
    "BitCast",
    "ArrayToPointerDecay",
    "NoOp",
}


def walk(node):
    yield node
    for child in node.get("inner", []):
        yield from walk(child)


def strip(node):
    for _ in range(16):
        kind = node.get("kind")
        if kind == "ParenExpr" or (kind == "ImplicitCastExpr" and node.get("castKind") in CASTS):
            children = node.get("inner", [])
            if len(children) != 1:
                break
            node = children[0]
        else:
            return node
    return node


def ref(node):
    node = strip(node)
    return node.get("referencedDecl", {}) if node.get("kind") == "DeclRefExpr" else {}


def constant(node, index):
    node = strip(node)
    if node.get("kind") == "IntegerLiteral":
        return int(node["value"])
    declaration = index.get(ref(node).get("id"), {})
    if declaration.get("constexpr") and len(declaration.get("inner", [])) == 1:
        literal = strip(declaration["inner"][0])
        if literal.get("kind") == "IntegerLiteral":
            return int(literal["value"])
    return None


def callee(node):
    if node.get("kind") != "CallExpr" or not node.get("inner"):
        return {}
    return ref(node["inner"][0])


def sink_shape_hash(node):
    # All node kinds survive normalization; only process-local IDs/locations disappear.
    shape = []
    for child in walk(node):
        target = child.get("referencedDecl", {})
        shape.append(
            [
                child.get("kind"),
                child.get("name"),
                child.get("opcode"),
                child.get("castKind"),
                child.get("value"),
                child.get("isArrow"),
                child.get("isPostfix"),
                child.get("type", {}).get("qualType"),
                target.get("kind"),
                target.get("name"),
                target.get("type", {}).get("qualType"),
            ]
        )
    return hashlib.sha256(json.dumps(shape, separators=(",", ":")).encode()).hexdigest()


def resolve(ast, source):
    if (
        not isinstance(ast, dict)
        or ast.get("kind") != "TranslationUnitDecl"
        or not isinstance(ast.get("inner"), list)
    ):
        raise ValueError("malformed AST: expected TranslationUnitDecl with inner list")
    index = {n["id"]: n for n in walk(ast) if n.get("id") and n.get("kind", "").endswith("Decl")}
    records = {
        n.get("name"): n
        for n in ast["inner"]
        if n.get("kind") == "CXXRecordDecl" and n.get("completeDefinition")
    }
    candidates = []
    seen = set()
    for function in ast["inner"]:
        if function.get("kind") != "FunctionDecl":
            continue
        blocks = [n for n in function.get("inner", []) if n.get("kind") == "CompoundStmt"]
        if not blocks:
            continue
        block = blocks[0]
        for call in walk(block):
            if callee(call).get("name") != "clif_send" or call.get("id") in seen:
                continue
            seen.add(call["id"])
            item = {
                "call_ast_id": call["id"],
                "function_decl_id": function["id"],
                "function": function.get("name"),
                "call_range": call.get("range"),
                "decision": "UNRESOLVED",
                "header_constant": None,
                "object_decl_id": None,
                "object_type": None,
                "reason": None,
                "evidence": [],
            }
            candidates.append(item)

            def deny(reason):
                item["reason"] = reason

            args = call.get("inner", [])[1:]
            if len(args) != 4:
                deny("unsupported sink arity")
                continue
            address = strip(args[0])
            if (
                address.get("kind") != "UnaryOperator"
                or address.get("opcode") != "&"
                or len(address.get("inner", [])) != 1
            ):
                deny("send pointer is not direct address of declaration")
                continue
            identity = ref(address["inner"][0])
            oid = identity.get("id")
            declaration = index.get(oid, {})
            item.update(
                object_decl_id=oid,
                object_type=declaration.get("type", {}).get("qualType"),
                object_decl_kind=declaration.get("kind"),
                object_name=declaration.get("name"),
            )

            def touches(node):
                return any(
                    n.get("kind") == "DeclRefExpr" and n.get("referencedDecl", {}).get("id") == oid
                    for n in walk(node)
                )

            writes = []
            escapes = []
            for node in walk(block):
                children = node.get("inner", [])
                if (
                    node.get("kind") in {"BinaryOperator", "CompoundAssignOperator"}
                    and node.get("opcode")
                    in {"=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="}
                    and children
                    and touches(children[0])
                ):
                    writes.append(
                        {"ast_id": node["id"], "kind": node["kind"], "opcode": node.get("opcode")}
                    )
                elif (
                    node.get("kind") == "UnaryOperator"
                    and node.get("opcode") in {"++", "--"}
                    and touches(node)
                ):
                    writes.append(
                        {"ast_id": node["id"], "kind": node["kind"], "opcode": node["opcode"]}
                    )
                elif node.get("kind") == "VarDecl" and node.get("id") != oid and touches(node):
                    escapes.append({"ast_id": node["id"], "kind": "alias_initializer"})
                elif (
                    node.get("kind") in {"CallExpr", "CXXMemberCallExpr", "CXXOperatorCallExpr"}
                    and node.get("id") != call["id"]
                    and touches(node)
                ):
                    escapes.append({"ast_id": node["id"], "kind": "unknown_call_escape"})
            item.update(
                target_write_count=len({w["ast_id"] for w in writes}),
                alias_or_escape_count=len({e["ast_id"] for e in escapes}),
            )
            item["evidence"].extend(writes + escapes)
            if call not in block.get("inner", []):
                deny("nested/lambda/conditional sender unsupported; declaration identity preserved")
                continue
            size = strip(args[1])
            if (
                size.get("kind") != "UnaryExprOrTypeTraitExpr"
                or size.get("name") != "sizeof"
                or len(size.get("inner", [])) != 1
                or ref(size["inner"][0]).get("id") != oid
            ):
                deny("sizeof is not bound to identical declaration")
                continue
            item["sizeof_decl_id"] = oid
            item["evidence"].append({"kind": "DeclRefExpr", "declaration_identity_match": True})
            target_stmts = [
                s
                for s in block.get("inner", [])
                if s.get("kind") == "DeclStmt"
                and any(v.get("id") == oid for v in s.get("inner", []))
            ]
            if (
                declaration.get("kind") != "VarDecl"
                or len(target_stmts) != 1
                or declaration.get("storageClass")
                or any(t in item["object_type"] for t in ["*", "&", "[", "volatile"])
            ):
                deny("object is not a direct local plain value")
                continue
            record = records.get(item["object_type"], {})
            fields = [n for n in record.get("inner", []) if n.get("kind") == "FieldDecl"]
            if (
                not fields
                or fields[0].get("name") != "PacketType"
                or fields[0]
                .get("type", {})
                .get("desugaredQualType", fields[0].get("type", {}).get("qualType"))
                != "unsigned short"
                or record.get("bases")
                or any(
                    n.get("kind") not in {"CXXRecordDecl", "FieldDecl"}
                    for n in record.get("inner", [])
                )
            ):
                deny("unsupported record layout/behavior")
                continue
            init = declaration.get("inner", [])
            if (
                len(init) != 1
                or init[0].get("kind") != "InitListExpr"
                or any(
                    n.get("kind") not in {"InitListExpr", "ImplicitValueInitExpr"}
                    for n in walk(init[0])
                )
            ):
                deny("unsupported object initializer")
                continue
            headers = []
            errors = []
            statements = block.get("inner", [])
            for position, stmt in enumerate(statements):
                n = strip(stmt)
                kind = n.get("kind")
                if stmt in target_stmts:
                    if position >= statements.index(call):
                        errors.append("declaration after send")
                elif kind == "DeclStmt":
                    for var in n.get("inner", []):
                        inn = var.get("inner", [])
                        if (
                            var.get("kind") != "VarDecl"
                            or len(inn) != 1
                            or strip(inn[0]).get("kind") not in {"StringLiteral", "IntegerLiteral"}
                        ):
                            errors.append("unsupported local initializer or alias/escape")
                elif kind == "BinaryOperator" and n.get("opcode") == "=":
                    lhs, rhs = n.get("inner", [{}, {}])
                    lhs = strip(lhs)
                    if (
                        lhs.get("kind") == "MemberExpr"
                        and not lhs.get("isArrow")
                        and lhs.get("referencedMemberDecl") == fields[0]["id"]
                        and len(lhs.get("inner", [])) == 1
                        and ref(lhs["inner"][0]).get("id") == oid
                    ):
                        value = constant(rhs, index)
                        headers.append(
                            {
                                "ast_id": n["id"],
                                "position": position,
                                "value": value,
                                "member_decl_id": fields[0]["id"],
                            }
                        )
                        if value is None or not 0 <= value <= 65535:
                            errors.append("unsupported header constant/conversion")
                        if position >= statements.index(call):
                            errors.append("header after send")
                    else:
                        errors.append("object/other assignment unsupported")
                elif stmt is call:
                    for arg in args[2:]:
                        if strip(arg).get("kind") not in {"IntegerLiteral", "DeclRefExpr"}:
                            errors.append("unsupported sink context expression")
                else:
                    errors.append("unsupported AST statement: " + str(kind))
            item["evidence"].extend(headers)
            if len(headers) != 1:
                errors.append("requires exactly one identity-bound header write")
            if errors:
                deny("; ".join(dict.fromkeys(errors)))
                continue
            sink = index.get(callee(call).get("id"), {})
            sink_blocks = [n for n in sink.get("inner", []) if n.get("kind") == "CompoundStmt"]
            sink_hash = None
            if len(sink_blocks) == 1:
                region = sink_blocks[0].get("range", {})
                begin, end = region.get("begin", {}), region.get("end", {})
                if (
                    isinstance(begin.get("offset"), int)
                    and isinstance(end.get("offset"), int)
                    and not begin.get("spellingLoc")
                    and not end.get("spellingLoc")
                ):
                    sink_hash = hashlib.sha256(
                        source[begin["offset"] : end["offset"] + end.get("tokLen", 1)]
                    ).hexdigest()
            item["fixture_sink_body_sha256"] = sink_hash
            shape_hash = sink_shape_hash(sink_blocks[0]) if len(sink_blocks) == 1 else None
            item["fixture_sink_ast_shape_sha256"] = shape_hash
            if (
                callee(call).get("kind") != "FunctionDecl"
                or sink_hash != "72b8df1285557d24295288c02833d27c371cbfc68c289c6627d3c934958d1242"
                or shape_hash != "7a917aba4f138cf0914bef782c7cebabbe735a4f0e71ee65417481ffef715da0"
            ):
                deny("unreviewed fixture sink contract")
                continue
            item.update(
                decision="FIXED_SIZEOF",
                header_constant=headers[0]["value"],
                reason=None,
                framing={
                    "kind": "sizeof_same_local",
                    "type": item["object_type"],
                    "numeric_length": None,
                },
            )
    return candidates


def semantic_ast_hash(ast):
    identities = {}

    def normalize(value):
        if isinstance(value, dict):
            return {k: normalize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [normalize(v) for v in value]
        if isinstance(value, str) and value.startswith("0x"):
            try:
                int(value[2:], 16)
            except ValueError:
                return value
            return identities.setdefault(value, "decl-" + str(len(identities)))
        return value

    return hashlib.sha256(
        json.dumps(normalize(ast), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def analyze(path, ast_artifact_path=None):
    data = pathlib.Path(path).read_bytes()
    command = [CLANG, *OPTIONS, str(pathlib.Path(path).resolve())]
    result = {
        "source": str(pathlib.Path(path).resolve()),
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "policy": "bounded-fixture-v1",
        "runtime_integration": False,
        "production_authority": False,
        "compiler": {"command": command, "ast_produced": False},
        "candidates": [],
    }
    try:
        process = subprocess.run(command, capture_output=True, text=True, timeout=30)
        result["compiler"].update(returncode=process.returncode, stderr=process.stderr)
        if process.returncode:
            raise ValueError("compiler rejected source")
        ast = json.loads(process.stdout)
        if ast_artifact_path is not None:
            pathlib.Path(ast_artifact_path).write_text(process.stdout)
        result["compiler"]["semantic_ast_sha256"] = semantic_ast_hash(ast)
        result["candidates"] = resolve(ast, data)
        result["compiler"]["ast_produced"] = True
    except (
        OSError,
        ValueError,
        subprocess.TimeoutExpired,
        KeyError,
        TypeError,
        RecursionError,
    ) as error:
        result["error"] = str(error)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = analyze(args.source)
    except OSError as error:
        result = {"error": str(error), "candidates": [], "production_authority": False}
    print(json.dumps(result, indent=2))
    raise SystemExit(2 if result.get("error") else 0)
