"""One captured execution input across real baseline/generation/repair phases."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

import pytest

from testpilot.loop import TestPilot
from testpilot.model import ModelError, ScriptedModel

INITIAL = "def amount():\n    return 2\n"
LATER = "def amount():\n    return 7\n"
DIFF = (
    "--- a/values.py\n+++ b/values.py\n@@ -1,2 +1,2 @@\n"
    " def amount():\n-    return 1\n+    return 2\n"
)


def generated(expected):
    return (
        "```python path=tests/test_generated.py\n"
        f"from values import amount\n\ndef test_generated():\n    assert amount() == {expected}\n"
        "```\n"
    )


def project(tmp_path, *, source=INITIAL, dependency=None, change_sandbox=False):
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "values.py").write_text(source, encoding="utf-8")
    if dependency is not None:
        (repo / "helper.py").write_text(dependency, encoding="utf-8")
    (repo / "tests/test_existing.py").write_text(
        "from values import amount\n\ndef test_existing():\n    assert amount() in (2, 7)\n",
        encoding="utf-8")
    events = tmp_path / "phase-events.jsonl"
    hook = (
        "from pathlib import Path\nimport json\n\n"
        "def pytest_sessionstart(session):\n"
        "    root = Path(__file__).parent\n"
        "    record = {'generated': (root / 'tests/test_generated.py').exists(),\n"
        "              'source': (root / 'values.py').read_text()}\n"
        "    if (root / 'helper.py').exists():\n"
        "        record['helper'] = (root / 'helper.py').read_text()\n"
        f"    with Path({str(events)!r}).open('a') as stream:\n"
        "        stream.write(json.dumps(record) + '\\n')\n"
    )
    if change_sandbox:
        hook += (
            "\ndef pytest_sessionfinish(session):\n"
            f"    Path(__file__).with_name('values.py').write_text({LATER!r})\n"
        )
    (repo / "conftest.py").write_text(hook, encoding="utf-8")
    return repo, events


def observations(events):
    return [json.loads(line) for line in events.read_text().splitlines()]


@pytest.mark.parametrize(("expectation", "status"), [(2, "passed"), (7, "failed")])
def test_generation_uses_initial_checkout_after_caller_edit(tmp_path, expectation, status):
    repo, events = project(tmp_path)
    replies = iter(["Test the selected function.", generated(expectation)])
    calls = 0

    def answer(model, messages):
        nonlocal calls
        calls += 1
        if calls == 1:
            # A caller edits their checkout while the planner is responding.
            (repo / "values.py").write_text(LATER, encoding="utf-8")
        return next(replies)

    result = TestPilot(ScriptedModel(answer), max_repair_rounds=0, coverage=False).run(repo, DIFF)
    assert result.status == status, result.final
    assert result.changed_functions[0]["source"] == INITIAL.rstrip("\n")
    assert [item["source"] for item in observations(events)] == [INITIAL, INITIAL]
    assert (repo / "values.py").read_text() == LATER
    assert len(result.ledger["entries"]) == 2


def test_unselected_dependency_is_captured_with_the_selected_source(tmp_path):
    source = "from helper import FACTOR\n\ndef amount():\n    return FACTOR\n"
    repo, events = project(tmp_path, source=source, dependency="FACTOR = 2\n")
    diff = "--- a/values.py\n+++ b/values.py\n@@ -4 +4 @@\n-    return 1\n+    return FACTOR\n"
    replies = iter(["Test the selected function.", generated(7)])
    calls = 0

    def answer(model, messages):
        nonlocal calls
        calls += 1
        if calls == 2:
            (repo / "helper.py").write_text("FACTOR = 7\n", encoding="utf-8")
        return next(replies)

    result = TestPilot(ScriptedModel(answer), max_repair_rounds=0, coverage=False).run(repo, diff)
    assert result.status == "failed", result.final
    assert [item["helper"] for item in observations(events)] == ["FACTOR = 2\n"] * 2
    assert (repo / "helper.py").read_text() == "FACTOR = 7\n"


def test_repair_uses_same_input_as_baseline_and_generation(tmp_path):
    repo, events = project(tmp_path)
    replies = iter(["Test the selected function.", generated(99), generated(2)])
    calls = 0

    def answer(model, messages):
        nonlocal calls
        calls += 1
        if calls == 3:
            (repo / "values.py").write_text(LATER, encoding="utf-8")
        return next(replies)

    result = TestPilot(ScriptedModel(answer), max_repair_rounds=1, coverage=False).run(repo, DIFF)
    assert result.status == "passed", result.final
    assert result.repair_rounds_used == 1
    assert [item["source"] for item in observations(events)] == [INITIAL] * 3
    assert [item["generated"] for item in observations(events)] == [False, True, True]
    assert (repo / "values.py").read_text() == LATER
    assert [item.kind for item in result.rounds] == ["generate", "repair"]


def test_pytest_writes_do_not_change_the_next_phase_input(tmp_path):
    repo, events = project(tmp_path, change_sandbox=True)
    result = TestPilot(ScriptedModel(["Test amount.", generated(2)]),
                       max_repair_rounds=0, coverage=False).run(repo, DIFF)
    assert result.status == "passed", result.final
    assert [item["source"] for item in observations(events)] == [INITIAL, INITIAL]
    assert (repo / "values.py").read_text() == INITIAL


@pytest.mark.parametrize("interrupt", [False, True], ids=["model-error", "keyboard-interrupt"])
def test_temporary_inputs_are_removed_when_model_work_stops(tmp_path, monkeypatch, interrupt):
    repo, events = project(tmp_path)
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temporary))

    def answer(model, messages):
        if interrupt:
            raise KeyboardInterrupt("authored model-stage interruption")
        raise ModelError("authored model failure")

    pilot = TestPilot(ScriptedModel(answer), coverage=False)
    if interrupt:
        with pytest.raises(KeyboardInterrupt, match="authored"):
            pilot.run(repo, DIFF)
    else:
        result = pilot.run(repo, DIFF)
        assert result.status == "model_error"
        assert result.test_files == {}
    assert len(observations(events)) == 1
    assert list(temporary.iterdir()) == []
    assert (repo / "values.py").read_text() == INITIAL


def test_empty_selection_keeps_existing_no_copy_behavior(tmp_path):
    client = ScriptedModel([])
    result = TestPilot(client, coverage=False).run(tmp_path / "absent-repository", "")
    assert result.status == "no_changes"
    assert result.test_files == {}
    assert client.calls == []
