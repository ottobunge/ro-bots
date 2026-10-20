"""Operational task labels must not advertise blocked lifecycle commands as usable."""

from pathlib import Path

import pytest
import yaml

TASKFILE = Path(__file__).resolve().parents[1] / "Taskfile.yml"


@pytest.mark.parametrize("task_name", ["playground"])
def test_unfinished_e2e_tasks_are_explicitly_labeled(task_name: str) -> None:
    tasks = yaml.safe_load(TASKFILE.read_text(encoding="utf-8"))["tasks"]
    assert "blocked" in tasks[task_name]["desc"].lower()


def test_e2e_chain_is_no_longer_blocked_and_runs_the_verified_cycle() -> None:
    """The e2e chain completed end-to-end (2026-10-20, ports 26900/26121/25121).

    The task must not advertise itself as blocked anymore; its command list is
    the verified clean-world cycle: teardown -> up -> init -> run -> assert ->
    teardown, each step owned by scripts/e2e/.
    """
    tasks = yaml.safe_load(TASKFILE.read_text(encoding="utf-8"))["tasks"]
    e2e = tasks["e2e"]
    assert "blocked" not in e2e["desc"].lower()
    chain = [entry["task"] for entry in e2e["cmds"]]
    assert chain == [
        "e2e-down",
        "e2e-up",
        "e2e-init",
        "e2e-run",
        "e2e-assert",
        "e2e-down",
    ]
    for name in dict.fromkeys(chain):
        step = tasks[name]
        assert "blocked" not in step["desc"].lower()
        assert step["cmds"] == [f"bash scripts/e2e/{name.removeprefix('e2e-')}.sh"]


def test_taskfile_offers_fixed_read_only_test_world_inspection() -> None:
    tasks = yaml.safe_load(TASKFILE.read_text(encoding="utf-8"))["tasks"]
    inspect = tasks.get("world:inspect")
    assert inspect is not None, "No runnable read-only test-world inspection task"
    assert inspect["cmds"] == [
        (
            "docker container ls --all --quiet --no-trunc "
            "--filter label=com.docker.compose.project=ro-bots-test"
        ),
        "docker volume ls --quiet --filter 'name=^ro-bots-world-test$'",
    ]
    assert "not authorization" in inspect["desc"].lower()


def test_wipe_task_does_not_advertise_an_environment_bypass() -> None:
    tasks = yaml.safe_load(TASKFILE.read_text(encoding="utf-8"))["tasks"]
    wipe = tasks["world:wipe"]
    assert "FORCE" not in wipe["desc"]
    assert wipe["cmds"] == ['bash scripts/world.sh wipe --world "$WORLD"']
    assert wipe["env"]["WORLD"] == '{{.world | default "test"}}'


@pytest.mark.parametrize("task_name", ["world:up", "world:down", "world:status"])
def test_compose_tasks_pass_selected_world_through_environment(task_name: str) -> None:
    tasks = yaml.safe_load(TASKFILE.read_text(encoding="utf-8"))["tasks"]
    task = tasks[task_name]
    operation = task_name.split(":")[1]
    assert task["env"]["WORLD"] == '{{.world | default "debug"}}'
    assert task["cmds"] == [f'bash scripts/world.sh {operation} --world "$WORLD"']
    assert "blocked" not in task["desc"].lower()
