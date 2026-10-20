import json
import os
import pathlib
import subprocess
import tempfile
import unittest

import trace_sender as t

AST = pathlib.Path("/home/otto/.hermes/cache/scratch/sender-proof-work/selected.json")


class ProofTests(unittest.TestCase):

    def test_real_declaration_send_sizeof_identity(self) -> None:
        r = t.trace(json.loads(AST.read_text()), "clif_emotion")
        assert r["identity_proven"], r
        assert r["object_id"] == r["send_object_id"]
        assert r["object_id"] == r["sizeof_object_id"]

    def test_real_header_and_gcc_layout_join(self) -> None:
        r = t.trace(
            json.loads(AST.read_text()),
            "clif_emotion",
            {"id": 192, "size": 7, "offsets": [0, 2, 6]},
        )
        assert r["decision"] == "IDENTITY_LAYOUT_CANDIDATE"
        assert r["header_value"] == 192
        assert r["measured_size"] == 7

    def test_unknown_helper_escape_denied_structurally(self) -> None:
        source = (
            "struct P { short h; }; const short H=1; void clif_send(const"
            " void*,unsigned); void mutate(P*); void f(){ P p{}; p.h=H; m"
            "utate(&p); clif_send(&p,sizeof(p)); }"
        )
        with tempfile.NamedTemporaryFile(
            suffix=".cpp", dir="/home/otto/.hermes/cache/scratch", mode="w"
        ) as f:
            f.write(source)
            f.flush()
            q = subprocess.run(
                [
                    (
                        "/nix/store/2msw5nclhpsm80z65dqmjiv8kkras989-clang-wrapper-21"
                        ".1.8/bin/clang++"
                    ),
                    "-std=c++17",
                    "-fsyntax-only",
                    "-Xclang",
                    "-ast-dump=json",
                    f.name,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        r = t.trace(json.loads(q.stdout)["inner"], "f", {"id": 1, "size": 2, "offsets": [0]})
        assert r["decision"] == "UNRESOLVED", r
        assert "unsupported statement" in str(r["reasons"])

    def test_wrong_authorities_rejected_before_candidate(self) -> None:
        for change in (
            {"profile": "20211103"},
            {"source_sha": "wrong"},
            {"layout_sha": "wrong"},
            {"metadata_trusted": False},
        ):
            with self.subTest(change=change):
                assert not t.authority_gate(**change)


class ReviewedOmissionTests(unittest.TestCase):

    def compiled(self, source: str) -> t.TraceResult:
        root = pathlib.Path(
            os.environ.get("SENDER_REPAIR_EVIDENCE", "/home/otto/.hermes/cache/scratch")
        )
        with tempfile.NamedTemporaryFile(suffix=".cpp", dir=root, mode="w", delete=False) as f:
            f.write(source)
            f.flush()
            path = pathlib.Path(f.name)
        q = subprocess.run(
            ["clang++", "-std=c++17", "-fsyntax-only", "-Xclang", "-ast-dump=json", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        path.with_suffix(".stdout").write_text(q.stdout)
        path.with_suffix(".stderr").write_text(q.stderr)
        assert q.returncode == 0, q.stderr
        return t.trace(json.loads(q.stdout)["inner"], "f", {"id": 1, "size": 8, "offsets": [0, 4]})

    def test_l1_helper_in_third_or_fourth_send_argument(self) -> None:
        for args in ("mutate(&p),AREA", "&bl,mutate(&p)"):
            with self.subTest(args=args):
                r = self.compiled(
                    (
                        "struct P { short h; int x; }; const short H=1; struct B {}; "
                        "enum Target { AREA }; void clif_send(const void*,unsigned,.."
                        ".); int mutate(P* p){p->h=2;return 0;} void f(B& bl){P p{};p"
                        ".h=H;clif_send(&p,sizeof(p),"
                    )
                    + args
                    + ");}"
                )
                assert r["decision"] == "UNRESOLVED", r

    def test_l1_plain_actual_pointer_and_area_guard(self) -> None:
        r = self.compiled(
            "struct P { short h; int x; }; const short H=1; struct B {}; "
            "enum Target { AREA }; void clif_send(const void*,unsigned,co"
            "nst B*,Target); void f(const B& bl){P p{};p.h=H;clif_send(&p"
            ",sizeof(p),&bl,AREA);}"
        )
        assert r["decision"] == "IDENTITY_LAYOUT_CANDIDATE", r

    def test_l2_mutable_header_is_not_an_immutable_constant(self) -> None:
        r = self.compiled(
            "struct P { short h; int x; }; short H=1; void clif_send(cons"
            "t void*,unsigned); void f(){P p{};p.h=H;clif_send(&p,sizeof("
            "p));}"
        )
        assert r["decision"] == "UNRESOLVED", r

    def test_l2_const_and_constexpr_integral_header_guards(self) -> None:
        for qualifier in ("const", "constexpr"):
            with self.subTest(qualifier=qualifier):
                r = self.compiled(
                    "struct P { short h; int x; }; "
                    + qualifier
                    + (
                        " short H=1; void clif_send(const void*,unsigned); void f(){P"
                        " p{};p.h=H;clif_send(&p,sizeof(p));}"
                    )
                )
                assert r["decision"] == "IDENTITY_LAYOUT_CANDIDATE", r

    def test_l3_float_parameter_cast_is_not_integral_plain_read(self) -> None:
        r = self.compiled(
            "struct P { short h; int x; }; const short H=1; void clif_sen"
            "d(const void*,unsigned); void f(float value){P p{};p.h=H;p.x"
            "=static_cast<int>(value);clif_send(&p,sizeof(p));}"
        )
        assert r["decision"] == "UNRESOLVED", r

    def test_l3_enum_to_integral_and_const_void_address_guard(self) -> None:
        r = self.compiled(
            "struct P { short h; int x; }; const short H=1; enum E { ONE="
            "1 }; void clif_send(const void*,unsigned); void f(E value){P"
            " p{};p.h=H;p.x=static_cast<int>(value);clif_send(&p,sizeof(p"
            "));}"
        )
        assert r["decision"] == "IDENTITY_LAYOUT_CANDIDATE", r


class RecordShapeTests(unittest.TestCase):

    def compiled_record(self, source: str) -> tuple[pathlib.Path, list[t.ASTNode]]:
        root = pathlib.Path(
            os.environ.get("SENDER_REPAIR_EVIDENCE", "/home/otto/.hermes/cache/scratch")
        )
        with tempfile.NamedTemporaryFile(suffix=".cpp", dir=root, mode="w", delete=False) as f:
            f.write(source)
            path = pathlib.Path(f.name)
        q = subprocess.run(
            ["clang++", "-std=c++17", "-fsyntax-only", "-Xclang", "-ast-dump=json", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        path.with_suffix(".ast.json").write_text(q.stdout)
        path.with_suffix(".clang.stderr").write_text(q.stderr)
        assert q.returncode == 0, q.stderr
        return (path, json.loads(q.stdout)["inner"])

    def test_l4_defined_union_overwrite_denied_before_metadata(self) -> None:
        source = (
            "#include <cstdio>\n#include <cstddef>\n#include <cstring>\nunio"
            "n P { unsigned short h; unsigned int x; }; const unsigned sh"
            "ort H=1;\nvoid clif_send(const void* p,unsigned n){unsigned s"
            'hort h;std::memcpy(&h,p,sizeof h);std::printf("sent_header=%'
            'u size=%u\\n",h,n);}\nvoid f(unsigned value){P p{};p.h=H;p.x=v'
            'alue;clif_send(&p,sizeof p);}\nint main(){std::printf("{\\"id\\'
            '":%u,\\"size\\":%zu,\\"offsets\\":[%zu,%zu]}\\n",H,sizeof(P),offs'
            "etof(P,h),offsetof(P,x));f(2);}\n"
        )
        path, nodes = self.compiled_record(source)
        q = subprocess.run(
            ["g++", "-std=c++17", str(path), "-o", str(path.with_suffix(".bin"))],
            capture_output=True,
            text=True,
            check=False,
        )
        path.with_suffix(".gcc.stderr").write_text(q.stderr)
        assert q.returncode == 0, q.stderr
        q = subprocess.run(
            [str(path.with_suffix(".bin"))], capture_output=True, text=True, check=True
        )
        path.with_suffix(".gcc.stdout").write_text(q.stdout)
        assert q.stdout == '{"id":1,"size":4,"offsets":[0,0]}\nsent_header=2 size=4\n'
        measured = json.loads(q.stdout.splitlines()[0])
        for metadata in (measured, None):
            r = t.trace(nodes, "f", metadata)
            path.with_suffix(".result.json").write_text(json.dumps(r, indent=2))
            assert r["decision"] == "UNRESOLVED", r
            assert "unsupported record shape" in str(r["reasons"])

    def test_l4_unsupported_layout_forms_fail_before_metadata(self) -> None:
        records = (
            "struct B {}; struct P : B { short h; int x; };",
            "struct P { short h : 16; int x; };",
            "struct P { short h; union { int x; unsigned y; }; };",
            "struct P { short h; [[no_unique_address]] int x; };",
            "struct P { short h; int x[1]; };",
            "struct P { short h; volatile int x; };",
            "struct Q { int y; }; struct P { short h; Q x; };",
            "struct __attribute__((ms_struct)) P { short h; int x; };",
        )
        for record in records:
            with self.subTest(record=record):
                _, nodes = self.compiled_record(
                    record
                    + (
                        " const short H=1; void clif_send(const void*,unsigned); void"
                        " f(){P p{};p.h=H;clif_send(&p,sizeof p);}"
                    )
                )
                for measured in (None, t.Measurement(id=1, size=8, offsets=[0, 4])):
                    r = t.trace(nodes, "f", measured)
                    assert r["decision"] == "UNRESOLVED", r
                    assert "unsupported record shape" in str(r["reasons"])

    def test_l4_ordinary_packed_short_aliases_remain_candidates(self) -> None:
        for base in ("short", "unsigned short"):
            source = (
                "#include <cstdio>\n#include <cstddef>\nusing Header = BASE;\nst"
                "atic_assert(sizeof(Header)==2);\n#pragma pack(push,1)\nstruct "
                "__attribute__((packed)) P { Header h; unsigned int x; unsign"
                "ed char y; };\n#pragma pack(pop)\nconst Header H=1; void clif_"
                "send(const void*,unsigned);\nvoid f(){P p{};p.h=H;p.x=2;p.y=3"
                ";clif_send(&p,sizeof p);}\nvoid clif_send(const void*,unsigne"
                'd){}\nint main(){std::printf("{\\"id\\":%u,\\"size\\":%zu,\\"offse'
                'ts\\":[%zu,%zu,%zu]}\\n",unsigned(H),sizeof(P),offsetof(P,h),o'
                "ffsetof(P,x),offsetof(P,y));}\n"
            ).replace("BASE", base)
            path, nodes = self.compiled_record(source)
            subprocess.run(
                ["g++", "-std=c++17", str(path), "-o", str(path.with_suffix(".bin"))],
                capture_output=True,
                text=True,
                check=True,
            )
            q = subprocess.run(
                [str(path.with_suffix(".bin"))], capture_output=True, text=True, check=True
            )
            path.with_suffix(".gcc.stdout").write_text(q.stdout)
            measured = json.loads(q.stdout)
            assert measured == {"id": 1, "size": 7, "offsets": [0, 2, 6]}
            assert t.trace(nodes, "f", measured)["decision"] == "IDENTITY_LAYOUT_CANDIDATE"

    def test_l4_header_requires_short_word_representation(self) -> None:
        _, nodes = self.compiled_record(
            "struct P { int h; int x; }; const int H=1; void clif_send(co"
            "nst void*,unsigned); void f(){P p{};p.h=H;clif_send(&p,sizeo"
            "f p);}"
        )
        r = t.trace(nodes, "f", {"id": 1, "size": 8, "offsets": [0, 4]})
        assert r["decision"] == "UNRESOLVED", r
        assert "unsupported record header representation" in str(r["reasons"])

    def test_field_level_packed_attribute_denied_before_metadata(self) -> None:
        source = (
            "#include <cstdio>\n#include <cstddef>\n#include <cstring>\nstru"
            "ct P { unsigned short h; unsigned int x __attribute__((packe"
            "d)); };\nconst unsigned short H=1;\nvoid clif_send(const void*"
            " p,unsigned n){unsigned short h;std::memcpy(&h,p,sizeof h);s"
            'td::printf("sent_header=%u size=%u\\n",h,n);}\nvoid f(){P p{};'
            "p.h=H;p.x=2;clif_send(&p,sizeof p);}\nint main(){std::printf("
            '"{\\"id\\":%u,\\"size\\":%zu,\\"offsets\\":[%zu,%zu]}\\n",H,sizeof('
            "P),offsetof(P,h),offsetof(P,x));f();}\n"
        )
        path, nodes = self.compiled_record(source)
        q = subprocess.run(
            ["g++", "-std=c++17", str(path), "-o", str(path.with_suffix(".bin"))],
            capture_output=True,
            text=True,
            check=True,
        )
        path.with_suffix(".gcc.stderr").write_text(q.stderr)
        q = subprocess.run(
            [str(path.with_suffix(".bin"))], capture_output=True, text=True, check=True
        )
        path.with_suffix(".gcc.stdout").write_text(q.stdout)
        assert q.stdout == '{"id":1,"size":6,"offsets":[0,2]}\nsent_header=1 size=6\n'
        measured = json.loads(q.stdout.splitlines()[0])
        record = next(
            n
            for n in nodes
            if n.get("kind") == "CXXRecordDecl"
            and n.get("name") == "P"
            and n.get("completeDefinition")
        )
        field = next(
            n for n in record["inner"] if n.get("kind") == "FieldDecl" and n.get("name") == "x"
        )
        assert [n["kind"] for n in field["inner"]] == ["PackedAttr"]
        for metadata in (measured, None):
            r = t.trace(nodes, "f", metadata)
            assert r["decision"] == "UNRESOLVED", r
            assert "unsupported record shape" in str(r["reasons"])
            assert "header_value" not in r


if __name__ == "__main__":
    unittest.main()
