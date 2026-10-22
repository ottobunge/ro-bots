import hashlib
import importlib.util
import pathlib
import tempfile
import unittest

HERE = pathlib.Path(__file__).parent


def module():
    path = HERE / "replay.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("replay", path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


class ReplayTests(unittest.TestCase):
    def test_exact_configured_header_and_retained_source(self):
        obj = module()
        build = getattr(obj, "construct", None)
        self.assertTrue(callable(build), "exact public configured closure constructor missing")
        with tempfile.TemporaryDirectory() as scratch:
            root = pathlib.Path(scratch) / "public-source"
            result = build(root)
            self.assertEqual(
                hashlib.sha256((root / "src/custom/defines_post.hpp").read_bytes()).hexdigest(),
                "64e8ffea133190fd361801cbcbfd5bcc4fc2c499a93312f8ee347492f725ad4c",
            )
            self.assertEqual(
                hashlib.sha256((root / "src/common/core.cpp").read_bytes()).hexdigest(),
                "765d822dedc1c2fe5a92f22393690b80bf3e47253c5df4589d08386440e5700c",
            )
            self.assertEqual(
                hashlib.sha256((root / "src/common/runtime-root.hpp").read_bytes()).hexdigest(),
                "16636e986015152f0097b3026393b5f0825f54aacbbedc990d9191821db2e35c",
            )
            self.assertEqual(
                result["before"]["src/map/clif.cpp"], result["after"]["src/map/clif.cpp"]
            )
            with self.assertRaises(FileExistsError):
                build(root)

    def test_unreviewed_flags_and_hash_drift_denied_before_compiler(self):
        obj = module()
        gate = getattr(obj, "validate_flags", None)
        self.assertTrue(callable(gate), "precompiler reviewed flag gate missing")
        trusted = (obj.META / "map-cppflags.txt").read_text()
        for poison in [
            "@response",
            "-include evil.hpp",
            "-UPACKET_OBFUSCATION",
            "-fplugin=evil.so",
        ]:
            with self.assertRaises(ValueError):
                gate("map", trusted + " " + poison)
        with tempfile.TemporaryDirectory() as scratch:
            path = pathlib.Path(scratch) / "controlled-drift.txt"
            path.write_text("controlled hostile drift")
            with self.assertRaises(ValueError):
                obj.checked(path, "0" * 64)
        self.assertEqual(gate("map", trusted), trusted.split())

    def test_only_reviewed_source_differences_are_accepted(self):
        obj = module()
        gate = getattr(obj, "verify_diff", None)
        self.assertTrue(callable(gate), "source-difference allowlist gate missing")
        with tempfile.TemporaryDirectory() as scratch:
            result = obj.construct(pathlib.Path(scratch) / "public-source")
            self.assertEqual(
                gate(result),
                [
                    "src/common/core.cpp",
                    "src/common/runtime-root.hpp",
                    "src/custom/defines_post.hpp",
                ],
            )
            result["after"]["src/map/clif.cpp"] = "0" * 64
            with self.assertRaises(ValueError):
                gate(result)

    def test_real_oracles_and_sender_extraction_preserve_negative_control(self):
        obj = module()
        run = getattr(obj, "experiment", None)
        self.assertTrue(callable(run), "compiler-backed offline experiment missing")
        report = run()
        self.assertEqual(report["verdict"], "VALIDATED_BOUNDED_PROFILE_LAYOUT_AST")
        self.assertEqual(len(report["profiles"]), 8)
        self.assertTrue(all(p["matches_installed"] for p in report["profiles"]))
        self.assertTrue(report["original_negative_control"])
        self.assertEqual(set(report["asts"]), {"clif_emotion", "clif_name", "clif_sitting"})
        self.assertTrue(report["production_freeze"]["stable"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
