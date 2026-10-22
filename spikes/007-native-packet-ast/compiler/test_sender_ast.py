import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent


class SenderASTTests(unittest.TestCase):
    def test_real_emotion_identity(self):
        p = subprocess.run(
            [sys.executable, str(ROOT / "sender_ast.py"), "clif_emotion"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        data = json.loads(p.stdout)
        self.assertEqual(data["function"]["name"], "clif_emotion")
        packet = next(d for d in data["declarations"] if d.get("name") == "p")
        self.assertTrue(any(d.get("id") == packet["id"] for d in data["references"]))
        self.assertTrue(data["sizeof_nodes"])
        self.assertTrue(data["send_calls"])
        self.assertFalse(data["native_admission"])
        self.assertFalse(data["exact_installed_profile_verified"])
        self.assertTrue(data["observed_profile"]["obfuscation"])

    def test_wrong_profile_fails_closed(self):
        p = subprocess.run(
            [sys.executable, str(ROOT / "sender_ast.py"), "clif_emotion", "--profile", "20211103"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(p.returncode, 2)
        self.assertIn("unsupported profile", p.stderr)
        self.assertEqual(p.stdout, "")

    def test_missing_ast_fails_closed(self):
        path = ROOT / "clang-original-emotion.stdout"
        held = path.with_suffix(".held")
        path.rename(held)
        try:
            p = subprocess.run(
                [sys.executable, str(ROOT / "sender_ast.py"), "clif_emotion"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(p.returncode, 2)
            self.assertIn("missing AST", p.stderr)
            self.assertEqual(p.stdout, "")
        finally:
            held.rename(path)


if __name__ == "__main__":
    unittest.main()
