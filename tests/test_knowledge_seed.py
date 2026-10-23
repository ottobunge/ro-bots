"""The seed-knowledge renderer: base game-knowledge journal lines.

The coordinator renders these once for a new agent; the module must never
write anywhere itself. Fixtures are small fake sidecars in the real JSON
sidecar shape; the real-builds smoke skips when the sidecar dir is absent.
"""

import json
from pathlib import Path

import pytest

from robots.knowledge import seed


def _build_builds(root: Path) -> Path:
    """Fake build sidecars in the real JSON sidecar shape."""
    builds = root / "builds" / "pre-re"
    builds.mkdir(parents=True)
    for stem, payload in (
        (
            "swordman-grinder",
            {
                "class": "Swordman",
                "playstyle": "grinder",
                "summary": "Solo kill-speed: STR powers Bash/auto-attack.",
            },
        ),
        (
            "mage-aoe-control",
            {
                "class": "Mage",
                "playstyle": "evasive/lethal",
                "summary": "Fire wall kiter: cast-time control over raw damage.",
            },
        ),
    ):
        (builds / f"{stem}.json").write_text(json.dumps(payload), encoding="utf-8")
    return builds


@pytest.fixture
def fake_builds(tmp_path: Path) -> Path:
    return _build_builds(tmp_path)


class TestSeedKnowledge:
    def test_guild_line_cites_emperium(self, fake_builds: Path) -> None:
        lines = seed.seed_knowledge_lines(builds_dir=fake_builds)
        assert any("Emperium" in line and "714" in line for line in lines)

    def test_guild_wire_facts_line(self, fake_builds: Path) -> None:
        lines = seed.seed_knowledge_lines(builds_dir=fake_builds)
        assert any("0x0165" in line for line in lines)

    def test_leveling_pointer_line(self, fake_builds: Path) -> None:
        lines = seed.seed_knowledge_lines(builds_dir=fake_builds)
        assert any("Leveling Spots" in line for line in lines)

    def test_build_lines_from_sidecars(self, fake_builds: Path) -> None:
        lines = seed.seed_knowledge_lines(builds_dir=fake_builds)
        assert any("Swordman" in line and "grinder" in line for line in lines)
        assert any("Mage" in line and "Fire wall kiter" in line for line in lines)

    def test_shape_bounded_and_deterministic(self, fake_builds: Path) -> None:
        first = seed.seed_knowledge_lines(builds_dir=fake_builds)
        second = seed.seed_knowledge_lines(builds_dir=fake_builds)
        assert first == second
        assert isinstance(first, tuple)
        assert all(isinstance(line, str) for line in first)
        assert all(len(line) <= 160 for line in first)
        assert 2 <= len(first) <= 40

    def test_no_writes_to_memory_dirs(self, fake_builds: Path, tmp_path: Path) -> None:
        before = sorted(p.name for p in tmp_path.rglob("*"))
        seed.seed_knowledge_lines(builds_dir=fake_builds)
        after = sorted(p.name for p in tmp_path.rglob("*"))
        assert before == after

    def test_real_seed_lines_cite_known_builds(self) -> None:
        builds = Path.cwd() / "run/knowledge/builds/pre-re"
        if not builds.is_dir():
            pytest.skip("build sidecars absent")
        lines = seed.seed_knowledge_lines()
        assert any("Swordman" in line for line in lines)
        assert len(lines) >= 10
