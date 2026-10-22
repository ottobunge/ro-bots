import json
import pathlib
import subprocess
import unittest

HERE = pathlib.Path(__file__).parent
FIXTURE = pathlib.Path("/home/otto/.hermes/cache/scratch/nmg-final/comments_strings_positive.cpp")


class BindingTests(unittest.TestCase):
    def run_cli(self, source):
        result = subprocess.run(
            ["python3", str(HERE / "resolve.py"), str(source)], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_plain_local_header_sizeof_real_ast(self):
        result = self.run_cli(FIXTURE)
        self.assertTrue(result["compiler"]["ast_produced"])
        self.assertEqual(result["candidates"][0]["decision"], "FIXED_SIZEOF")
        self.assertEqual(result["candidates"][0]["header_constant"], 1)

    def test_lambda_parameter_identity_is_reported_not_outer_name(self):
        result = self.run_cli(FIXTURE.with_name("lambda_parameter.cpp"))
        self.assertEqual(len(result["candidates"]), 1)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["decision"], "UNRESOLVED")
        self.assertEqual(candidate["object_decl_kind"], "ParmVarDecl")
        self.assertEqual(candidate["object_type"], "PACKET_ZC_TWO")
        self.assertIsNone(candidate["header_constant"])

    def test_mutation_evidence_counts_identity_bound_writes(self):
        result = self.run_cli(FIXTURE.with_name("parenthesized_header_assignment.cpp"))
        candidate = result["candidates"][0]
        self.assertEqual(candidate["decision"], "UNRESOLVED")
        self.assertEqual(candidate.get("target_write_count"), 2)

    def test_alias_escape_evidence(self):
        result = self.run_cli(FIXTURE.with_name("alias_pointer_mutation.cpp"))
        candidate = result["candidates"][0]
        self.assertEqual(candidate["decision"], "UNRESOLVED")
        self.assertGreater(candidate.get("alias_or_escape_count", 0), 0)

    def test_unreviewed_sink_definition_fails_closed(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            source = pathlib.Path(directory) / "unreviewed_sink.cpp"
            source.write_text(
                FIXTURE.read_text().replace(
                    "std::printf(",
                    "++*const_cast<uint16_t*>(static_cast<const uint16_t*>(p)); std::printf(",
                )
            )
            candidate = self.run_cli(source)["candidates"][0]
            self.assertEqual(candidate["decision"], "UNRESOLVED")
            self.assertIn("sink", candidate["reason"])

    def test_sink_macro_semantics_not_just_body_bytes(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            source = pathlib.Path(directory) / "macro_sink.cpp"
            source.write_text(
                FIXTURE.read_text().replace(
                    "void clif_send",
                    "#define unsigned(x) (++*const_cast<uint16_t*>(static_cast<const uint16_t*>(p)), static_cast<unsigned>(x))\nvoid clif_send",
                )
            )
            candidate = self.run_cli(source)["candidates"][0]
            self.assertEqual(candidate["decision"], "UNRESOLVED")

    def test_real_ast_semantic_repeat_hash(self):
        first = self.run_cli(FIXTURE)
        second = self.run_cli(FIXTURE)
        self.assertTrue(first["compiler"].get("semantic_ast_sha256"))
        self.assertEqual(
            first["compiler"]["semantic_ast_sha256"], second["compiler"]["semantic_ast_sha256"]
        )

    def test_compiler_rejection_preserves_diagnostics(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            source = pathlib.Path(directory) / "invalid.cpp"
            source.write_text("not valid C++")
            result = subprocess.run(
                ["python3", str(HERE / "resolve.py"), str(source)], capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 2)
            output = json.loads(result.stdout)
            self.assertFalse(output["compiler"]["ast_produced"])
            self.assertTrue(output["compiler"]["stderr"])
            self.assertEqual(output["candidates"], [])

    def test_missing_compiler_fails_closed(self):
        # Negative-only dependency failure injection; no substitute AST/admission.
        import resolve

        original = resolve.CLANG
        try:
            resolve.CLANG = "/nonexistent/review-test-clang++"
            result = resolve.analyze(FIXTURE)
        finally:
            resolve.CLANG = original
        self.assertFalse(result["compiler"]["ast_produced"])
        self.assertIn("No such file", result["error"])
        self.assertEqual(result["candidates"], [])

    def test_malformed_ast_is_denied_not_accepted_fixture(self):
        import resolve

        with self.assertRaisesRegex(ValueError, "malformed AST"):
            resolve.resolve({"kind": "garbage"}, b"")


if __name__ == "__main__":
    unittest.main()
