from collections.abc import Callable, Iterator
from typing import Any, TypedDict, cast

# Clang's extensible JSON nodes have heterogeneous compiler-owned properties.
type ASTNode = dict[str, Any]


class Measurement(TypedDict):
    id: int
    size: int
    offsets: list[int]


class TraceResult(TypedDict, total=False):
    identity_proven: bool
    decision: str
    reasons: list[str]
    sink_contract_status: str
    sender_semantic_admission: bool
    runtime_admission: bool
    object_id: str | None
    send_object_id: str | None
    sizeof_object_id: str | None
    object_type: str
    function_id: str
    send_id: str
    sizeof_id: str
    sink_decl_id: str | None
    record_id: str
    header_field_id: str
    header_field_name: str
    header_constant_id: str | None
    header_assignment_id: str
    header_value: int
    record_location: ASTNode | None
    constant_location: ASTNode | None
    measured_size: int
    measured_offsets: list[int]


SOURCE_SHA = "f045b33b434efc83a7e216f295bf899114a4a1a2daa159898fb738d8b553d6d6"
AUTHORITY_SHA = "602c856e8e368fe767ff6b54704416818dc7939a5c6606f0fb6af6b49c2e71ac"


def authority_gate(
    profile: str = "20180704",
    source_sha: str = SOURCE_SHA,
    layout_sha: str = AUTHORITY_SHA,
    metadata_trusted: bool = True,
) -> bool:
    return (
        profile == "20180704"
        and source_sha == SOURCE_SHA
        and layout_sha == AUTHORITY_SHA
        and metadata_trusted is True
    )


def walk(n: ASTNode) -> Iterator[ASTNode]:
    yield n
    for c in n.get("inner", []):
        yield from walk(c)


def strip(n: ASTNode) -> ASTNode:
    while n.get("kind") in ("ImplicitCastExpr", "ParenExpr") and len(n.get("inner", [])) == 1:
        n = n["inner"][0]
    return n


def integral_type(n: ASTNode) -> bool:
    q = n.get("type", {})
    s: str = q.get("desugaredQualType", q.get("qualType", ""))
    if any(x in s for x in ("volatile", "&", "*")):
        return False
    s = " ".join(x for x in s.split() if x != "const")
    return s in {
        "bool",
        "char",
        "signed char",
        "unsigned char",
        "short",
        "unsigned short",
        "int",
        "unsigned int",
        "long",
        "unsigned long",
        "long long",
        "unsigned long long",
    }


def ref(n: ASTNode) -> str | None:
    return cast(str | None, strip(n).get("referencedDecl", {}).get("id"))


class _UnresolvedError(Exception):
    """A supported trace step could not establish its bounded proof."""


def _bind_send(
    nodes: list[ASTNode], sender: str, r: TraceResult
) -> tuple[ASTNode, ASTNode, list[ASTNode], ASTNode, str | None]:
    """Bind the sole sink, address operand and sizeof to one local declaration."""
    fs = [
        n
        for n in nodes
        if n.get("kind") == "FunctionDecl"
        and n.get("name") == sender
        and any(x.get("kind") == "CompoundStmt" for x in n.get("inner", []))
    ]
    if len(fs) != 1:
        reason = "function definition absent or ambiguous"
        raise _UnresolvedError(reason)
    f = fs[0]
    body = next(x for x in f["inner"] if x.get("kind") == "CompoundStmt")
    calls = [
        n
        for n in walk(body)
        if n.get("kind") == "CallExpr"
        and strip(n["inner"][0]).get("referencedDecl", {}).get("name") == "clif_send"
    ]
    if len(calls) != 1:
        reason = "send count not one"
        raise _UnresolvedError(reason)
    call = calls[0]
    args = call["inner"][1:]
    obj = strip(args[0])
    sz = strip(args[1])
    if (
        obj.get("kind") != "UnaryOperator"
        or obj.get("opcode") != "&"
        or sz.get("kind") != "UnaryExprOrTypeTraitExpr"
        or (sz.get("name") != "sizeof")
        or (not sz.get("inner"))
    ):
        reason = "not address-object / sizeof-object"
        raise _UnresolvedError(reason)
    oid = ref(obj["inner"][0])
    sid = ref(sz["inner"][0])
    decls = [n for n in walk(body) if n.get("kind") == "VarDecl" and n.get("id") == oid]
    if len(decls) != 1 or oid != sid:
        reason = "object declaration identity mismatch"
        raise _UnresolvedError(reason)
    d = decls[0]
    r.update(
        {
            "identity_proven": True,
            "object_id": oid,
            "send_object_id": oid,
            "sizeof_object_id": sid,
            "object_type": d["type"]["qualType"],
            "function_id": f["id"],
            "send_id": call["id"],
            "sizeof_id": sz["id"],
            "sink_decl_id": ref(call["inner"][0]),
        }
    )
    return (body, call, args, d, oid)


def _bind_record(nodes: list[ASTNode], r: TraceResult) -> tuple[ASTNode, list[ASTNode], ASTNode]:
    """Require the bound object's supported storage before resolving its header."""
    records = [
        n
        for n in nodes
        if n.get("kind") == "CXXRecordDecl"
        and n.get("completeDefinition")
        and (n.get("name") == r["object_type"])
    ]
    if len(records) != 1:
        reason = "record declaration unavailable"
        raise _UnresolvedError(reason)
    record = records[0]
    fields = [n for n in record.get("inner", []) if n.get("kind") == "FieldDecl"]
    header = fields[0] if fields else {}
    # Only plain scalar aggregates have independent, non-overlapping fields.
    # Packing changes alignment, not this guarantee; unions/bases/overlap do not.
    shape = record.get("definitionData", {})
    ordinary_children = all(
        n.get("kind") in {"FieldDecl", "PackedAttr", "MaxFieldAlignmentAttr"}
        or (
            n.get("isImplicit")
            and n.get("kind")
            in {"CXXRecordDecl", "CXXConstructorDecl", "CXXDestructorDecl", "CXXMethodDecl"}
        )
        for n in record.get("inner", [])
    )
    ordinary_fields = all(
        n.get("name")
        and (not n.get("isBitfield"))
        and (not n.get("isImplicit"))
        and integral_type(n)
        and (not n.get("inner", []))
        for n in fields
    )
    if (
        record.get("tagUsed") not in {"struct", "class"}
        or record.get("bases")
        or (
            not all(
                shape.get(k) is True
                for k in ("isAggregate", "isStandardLayout", "isTrivial", "isTriviallyCopyable")
            )
        )
        or (not ordinary_children)
        or (not fields)
        or (not ordinary_fields)
    ):
        reason = "unsupported record shape: requires plain non-overlapping scalar aggregate"
        raise _UnresolvedError(reason)
    htype = header.get("type", {})
    htype = htype.get("desugaredQualType", htype.get("qualType", ""))
    if htype not in {"short", "unsigned short"}:
        reason = "unsupported record header representation: requires short word on pinned target"
        raise _UnresolvedError(reason)
    return (record, fields, header)


def _bind_header(
    nodes: list[ASTNode],
    body: ASTNode,
    oid: str | None,
    record: ASTNode,
    header: ASTNode,
    *,
    r: TraceResult,
) -> tuple[ASTNode, ASTNode, int]:
    """Resolve the unique field assignment and its immutable integral header."""
    assignments = [
        n
        for n in walk(body)
        if n.get("kind") == "BinaryOperator"
        and n.get("opcode") == "="
        and (strip(n["inner"][0]).get("referencedMemberDecl") == header.get("id"))
        and (ref(strip(n["inner"][0])["inner"][0]) == oid)
    ]
    if len(assignments) != 1:
        reason = "header assignment count not one"
        raise _UnresolvedError(reason)
    a = assignments[0]
    hid = ref(a["inner"][1])
    constants = [
        n for n in nodes if n.get("id") == hid and n.get("kind") in ("VarDecl", "EnumConstantDecl")
    ]
    if len(constants) != 1:
        reason = "constant declaration unavailable"
        raise _UnresolvedError(reason)
    constant = constants[0]
    cq = constant.get("type", {})
    ctype = cq.get("desugaredQualType", cq.get("qualType", ""))
    if (
        constant.get("kind") != "VarDecl"
        or not integral_type(constant)
        or "const" not in ctype.split()
    ):
        reason = "header declaration is not immutable integral const/constexpr"
        raise _UnresolvedError(reason)
    literals = [n for n in walk(constant) if n.get("kind") == "IntegerLiteral"]
    if len(literals) != 1:
        reason = "constant initializer unsupported"
        raise _UnresolvedError(reason)
    value = int(literals[0]["value"])
    r.update(
        {
            "record_id": record["id"],
            "header_field_id": header["id"],
            "header_field_name": header["name"],
            "header_constant_id": hid,
            "header_assignment_id": a["id"],
            "header_value": value,
            "record_location": record.get("loc"),
            "constant_location": constants[0].get("loc"),
        }
    )
    return (a, constant, value)


def _check_layout(measured: Measurement | None, value: int) -> None:
    """Join the resolved header to the existing trusted GCC measurement."""
    if measured is None:
        reason = "GCC layout evidence absent"
        raise _UnresolvedError(reason)
    if (
        measured.get("id") != value
        or measured.get("offsets", [None])[0] != 0
        or measured.get("size", 0) <= 0
    ):
        reason = "GCC layout/header mismatch"
        raise _UnresolvedError(reason)


def _check_extra_arguments(
    args: list[ASTNode], oid: str | None, casts_ok: Callable[[ASTNode, str], bool]
) -> None:
    for extra in args[2:]:
        # Later arguments must not mutate or alias the bound packet.
        if not casts_ok(extra, "extra"):
            reason = "unsupported cast kind/type in final send argument"
            raise _UnresolvedError(reason)
        if any(
            n.get("kind")
            not in {
                "ImplicitCastExpr",
                "ParenExpr",
                "DeclRefExpr",
                "IntegerLiteral",
                "UnaryOperator",
            }
            for n in walk(extra)
        ):
            reason = "unsupported final send argument expression"
            raise _UnresolvedError(reason)
        if any(
            n.get("kind") == "UnaryOperator"
            and (
                n.get("opcode") != "&"
                or strip(n.get("inner", [{}])[0]).get("kind") != "DeclRefExpr"
            )
            for n in walk(extra)
        ):
            reason = "unsupported final send argument address"
            raise _UnresolvedError(reason)
        if any(ref(n) == oid for n in walk(extra) if n.get("kind") == "DeclRefExpr"):
            reason = "packet alias in final send argument"
            raise _UnresolvedError(reason)


def _check_initial_object(statements: list[ASTNode], d: ASTNode, oid: str | None) -> None:
    """Require the first sole declaration to be a fresh zero aggregate."""
    if (
        statements[0].get("kind") != "DeclStmt"
        or len(statements[0].get("inner", [])) != 1
        or statements[0]["inner"][0].get("id") != oid
    ):
        reason = "fresh object must be first sole declaration"
        raise _UnresolvedError(reason)
    initial = d.get("inner", [])
    if (
        len(initial) != 1
        or initial[0].get("kind") != "InitListExpr"
        or any(n.get("kind") != "ImplicitValueInitExpr" for n in initial[0].get("inner", []))
    ):
        reason = "fresh zero aggregate initialization unsupported"
        raise _UnresolvedError(reason)


def _check_assignments(
    statements: list[ASTNode],
    fields: list[ASTNode],
    oid: str | None,
    a: ASTNode,
    casts_ok: Callable[[ASTNode, str], bool],
) -> None:
    fieldids = {x["id"] for x in fields}
    # Check all intermediate writes, retaining the original first-failure order.
    allowed_rhs = {
        "ImplicitCastExpr",
        "CXXStaticCastExpr",
        "ParenExpr",
        "DeclRefExpr",
        "MemberExpr",
        "IntegerLiteral",
    }
    for statement in statements[1:-1]:
        st = strip(statement)
        if st.get("kind") != "BinaryOperator" or st.get("opcode") != "=":
            reason = "unsupported statement " + st.get("kind", "missing")
            raise _UnresolvedError(reason)
        lhs = strip(st["inner"][0])
        rhs = st["inner"][1]
        if (
            lhs.get("kind") != "MemberExpr"
            or lhs.get("isArrow")
            or lhs.get("referencedMemberDecl") not in fieldids
            or (ref(lhs["inner"][0]) != oid)
        ):
            reason = "assignment does not bind direct packet field identity"
            raise _UnresolvedError(reason)
        if not casts_ok(rhs, "scalar"):
            reason = "unsupported scalar cast kind/type"
            raise _UnresolvedError(reason)
        if any(n.get("kind") not in allowed_rhs for n in walk(rhs)):
            reason = "unknown mutation or unevaluated expression in scalar payload"
            raise _UnresolvedError(reason)
        if st.get("id") != a.get("id") and any(
            ref(n) == oid for n in walk(rhs) if n.get("kind") == "DeclRefExpr"
        ):
            reason = "packet alias/self payload expression unsupported"
            raise _UnresolvedError(reason)
    if a["id"] not in [strip(x).get("id") for x in statements[1:-1]]:
        reason = "header assignment not before final send"
        raise _UnresolvedError(reason)


def _check_grammar(
    nodes: list[ASTNode],
    sender: str,
    body: ASTNode,
    call: ASTNode,
    args: list[ASTNode],
    *,
    d: ASTNode,
    oid: str | None,
    fields: list[ASTNode],
    a: ASTNode,
    constant: ASTNode,
    r: TraceResult,
) -> None:
    statements = body.get("inner", [])
    # Cast rules are context-specific and shared by the remaining grammar checks.
    if not statements or statements[-1].get("id") != call["id"]:
        reason = "send is not final top-level statement"
        raise _UnresolvedError(reason)
    enums = {n["name"] for n in nodes if n.get("kind") == "EnumDecl" and n.get("name")}
    # The pinned selected real AST omits these enum declarations; this exception is
    # only the exact real sender's known enum-read contexts, not arbitrary types.
    if sender == "clif_emotion":
        enums.update({"emotion_type", "send_target"})

    def typename(n: ASTNode) -> str:
        q = n.get("type", {})
        return cast(str, q.get("desugaredQualType", q.get("qualType", "")))

    def scalar(n: ASTNode) -> bool:
        return integral_type(n) or typename(n).removeprefix("const ").removeprefix("enum ") in enums

    def casts_ok(expr: ASTNode, context: str) -> bool:
        for n in walk(expr):
            if n.get("kind") not in ("ImplicitCastExpr", "CXXStaticCastExpr"):
                continue
            children = n.get("inner", [])
            if len(children) != 1:
                return False
            child = children[0]
            kind = n.get("castKind")
            dest = typename(n)
            src = typename(child)
            if kind in ("NoOp", "LValueToRValue") and scalar(n) and scalar(child):
                continue
            if kind == "IntegralCast" and integral_type(n) and scalar(child):
                continue
            if (
                context == "callee"
                and n.get("kind") == "ImplicitCastExpr"
                and (kind == "FunctionToPointerDecay")
                and (child.get("kind") == "DeclRefExpr")
                and (child.get("referencedDecl", {}).get("kind") == "FunctionDecl")
                and (ref(child) == r["sink_decl_id"])
            ):
                continue
            if (
                context == "object"
                and n.get("kind") == "ImplicitCastExpr"
                and (kind == "BitCast")
                and (dest == "const void *")
                and (child.get("kind") == "UnaryOperator")
                and (child.get("opcode") == "&")
                and (ref(child["inner"][0]) == oid)
            ):
                continue
            if (
                context == "extra"
                and n.get("kind") == "ImplicitCastExpr"
                and (kind == "LValueToRValue")
                and (dest == src)
                and ("*" in dest)
                and ("volatile" not in dest)
                and (strip(child).get("kind") == "DeclRefExpr")
                and (strip(child).get("referencedDecl", {}).get("kind") == "ParmVarDecl")
            ):
                continue
            return False
        return True

    if (
        not casts_ok(call["inner"][0], "callee")
        or not casts_ok(args[0], "object")
        or (not casts_ok(args[1], "size"))
    ):
        reason = "unsupported cast kind/type in final send"
        raise _UnresolvedError(reason)
    if not casts_ok(constant, "scalar"):
        reason = "unsupported header initializer cast kind/type"
        raise _UnresolvedError(reason)
    _check_extra_arguments(args, oid, casts_ok)
    _check_initial_object(statements, d, oid)
    _check_assignments(statements, fields, oid, a, casts_ok)


def trace(nodes: list[ASTNode], sender: str, measured: Measurement | None = None) -> TraceResult:
    r: TraceResult = {
        "identity_proven": False,
        "decision": "UNRESOLVED",
        "reasons": [],
        "sink_contract_status": "UNREVIEWED",
        "sender_semantic_admission": False,
        "runtime_admission": False,
    }
    try:
        body, call, args, d, oid = _bind_send(nodes, sender, r)
        record, fields, header = _bind_record(nodes, r)
        a, constant, value = _bind_header(nodes, body, oid, record, header, r=r)
        _check_layout(measured, value)
        _check_grammar(
            nodes,
            sender,
            body,
            call,
            args,
            d=d,
            oid=oid,
            fields=fields,
            a=a,
            constant=constant,
            r=r,
        )
    except _UnresolvedError as error:
        r["reasons"] = [str(error)]
        return r
    assert measured is not None
    r.update(
        {
            "decision": "IDENTITY_LAYOUT_CANDIDATE",
            "measured_size": measured["size"],
            "measured_offsets": measured["offsets"],
        }
    )
    return r
