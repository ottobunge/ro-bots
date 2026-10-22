"""Candidate-only readback CLI; no caller compiler flags or metadata inputs."""

import argparse, hashlib, json, pathlib, sys
import trace_sender as t

W = pathlib.Path("/home/otto/.hermes/cache/scratch/sender-proof-work")
A = pathlib.Path(
    "/home/otto/.hermes/cache/scratch/native-profile-replay-s2jdj4rn/output/result.json"
)
PINS = {
    "selected.json": "07238418270d5717f43aa169a51bd5f40c3e58598479831b25aa0d80af30f450",
    "fresh-gcc-layout.stdout": "d79dfefd4be7efe0d6fbf3fd8cf7bfb135853dfe8935b39d758e7d99b3140ebf",
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("sender", choices=["clif_emotion", "clif_name", "clif_sitting"])
    p.add_argument("--profile", default="20180704")
    a = p.parse_args()
    try:
        if not t.authority_gate(profile=a.profile):
            raise ValueError("unsupported profile; denied before candidate")
        if sha(A) != t.AUTHORITY_SHA:
            raise ValueError("untrusted authority metadata")
        authority = json.loads(A.read_text())
        inv = pathlib.Path(authority["inventory"]["path"])
        if sha(inv) != authority["inventory"]["sha256"]:
            raise ValueError("inventory mismatch")
        inventory = json.loads(inv.read_text())
        source = A.parent.parent / "public-source"
        if any(sha(source / f) != h for f, h in inventory["after"].items()):
            raise ValueError("source closure changed")
        if any(sha(W / f) != h for f, h in PINS.items()):
            raise ValueError("AST or measured layout artifact changed")
        nodes = json.loads((W / "selected.json").read_text())
        measured = json.loads((W / "fresh-gcc-layout.stdout").read_text())["emotion"]
        result = t.trace(nodes, a.sender, measured if a.sender == "clif_emotion" else None)
        result.update(
            sender=a.sender,
            source_closure_sha256=t.SOURCE_SHA,
            authority_sha256=t.AUTHORITY_SHA,
            ast_artifact_sha256=PINS["selected.json"],
            gcc_layout_artifact_sha256=PINS["fresh-gcc-layout.stdout"],
        )
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as e:
        print(
            json.dumps(
                {
                    "decision": "DENIED",
                    "reasons": [str(e)],
                    "runtime_admission": False,
                    "sender_semantic_admission": False,
                }
            )
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
