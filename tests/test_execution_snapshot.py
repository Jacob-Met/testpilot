"""One captured execution input across real baseline/generation/repair phases."""
from __future__ import annotations

import json
from pathlib import Path
import stat
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


def test_removed_existing_test_is_retained_and_generated_path_stays_new(tmp_path):
    repo, events = project(tmp_path)
    existing = repo / "tests/test_generated.py"
    existing.write_text("def test_original_failure():\n    assert False\n", encoding="utf-8")
    replies = iter(["Test amount.", generated(2)])
    calls = 0

    def answer(model, messages):
        nonlocal calls
        calls += 1
        if calls == 1:
            existing.unlink()
        return next(replies)

    result = TestPilot(ScriptedModel(answer), max_repair_rounds=0, coverage=False).run(repo, DIFF)
    assert result.status == "failed", result.final
    assert "tests/test_generated.py" not in result.test_files
    assert "tests/test_generated_testpilot.py" in result.test_files
    assert any("test_original_failure" in c["nodeid"] and c["outcome"] == "failed"
               for c in result.final["cases"])
    assert not existing.exists()


def test_module_name_of_removed_existing_test_remains_reserved(tmp_path):
    repo, events = project(tmp_path)
    (repo / "checks").mkdir()
    existing = repo / "checks/test_generated.py"
    existing.write_text("def test_original_check():\n    assert True\n", encoding="utf-8")
    (repo / "pytest.ini").write_text("[pytest]\ntestpaths = checks\n", encoding="utf-8")
    replies = iter(["Test amount.", generated(2)])
    calls = 0

    def answer(model, messages):
        nonlocal calls
        calls += 1
        if calls == 1:
            existing.unlink()
        return next(replies)

    result = TestPilot(ScriptedModel(answer), max_repair_rounds=0, coverage=False).run(repo, DIFF)
    assert result.status == "passed", result.final
    assert "tests/test_generated_testpilot.py" in result.test_files
    assert any("test_original_check" in c["nodeid"] and c["outcome"] == "passed"
               for c in result.final["cases"])
    assert not existing.exists()


@pytest.mark.parametrize("absolute", [False, True], ids=["relative-link", "absolute-link"])
def test_internal_source_links_preserve_explicit_alias_identity(tmp_path, absolute):
    repo, events = project(tmp_path)
    (repo / "alias.py").symlink_to(repo / "values.py" if absolute else "values.py")
    result = TestPilot(ScriptedModel(["Test amount.", generated(2)]),
                       max_repair_rounds=0, coverage=False).run(
                           repo, DIFF, targets=["alias.py::amount", "values.py::amount"])
    assert result.status == "passed", result.final
    assert len(result.changed_functions) == 1
    assert result.changed_functions[0]["path"] == "alias.py"
    assert result.changed_functions[0]["changed_lines"] == [2]
    assert (repo / "alias.py").is_symlink()


def test_source_alias_to_ignored_directory_keeps_its_runtime_bytes(tmp_path):
    repo, events = project(tmp_path)
    (repo / ".venv").mkdir()
    (repo / ".venv/values.py").write_text(INITIAL, encoding="utf-8")
    (repo / "values.py").unlink()
    (repo / "values.py").symlink_to(".venv/values.py")
    result = TestPilot(ScriptedModel(["Test amount.", generated(2)]),
                       max_repair_rounds=0, coverage=False).run(repo, DIFF)
    assert result.status == "passed", result.final
    assert result.changed_functions[0]["source"] == INITIAL.rstrip("\n")
    assert [item["source"] for item in observations(events)] == [INITIAL, INITIAL]
    assert (repo / "values.py").is_symlink()


def test_relative_external_data_alias_keeps_existing_execution_behavior(tmp_path):
    source = "from helper import FACTOR\n\ndef amount():\n    return FACTOR\n"
    repo, events = project(tmp_path, source=source)
    outside = tmp_path / "outside.py"
    outside.write_text("FACTOR = 2\n", encoding="utf-8")
    (repo / "helper.py").symlink_to("../outside.py")
    diff = "--- a/values.py\n+++ b/values.py\n@@ -4 +4 @@\n-    return 1\n+    return FACTOR\n"
    result = TestPilot(ScriptedModel(["Test amount.", generated(2)]),
                       max_repair_rounds=0, coverage=False).run(repo, diff)
    assert result.status == "passed", result.final
    assert [item["helper"] for item in observations(events)] == ["FACTOR = 2\n"] * 2
    assert outside.read_text() == "FACTOR = 2\n"
    assert (repo / "helper.py").is_symlink()


def test_outward_selected_source_still_refuses_before_reading_it(tmp_path, monkeypatch):
    import builtins
    from testpilot.diff import DiffSourceError

    repo, events = project(tmp_path)
    outside = tmp_path / "outside.py"
    outside.write_text(INITIAL, encoding="utf-8")
    (repo / "values.py").unlink()
    (repo / "values.py").symlink_to(outside)
    original_open = builtins.open
    reads = []

    def observed_open(file, mode="r", *args, **kwargs):
        if isinstance(file, (str, Path)) and Path(file).resolve() == outside.resolve():
            reads.append((str(file), mode))
        return original_open(file, mode, *args, **kwargs)

    client = ScriptedModel([])
    monkeypatch.setattr(builtins, "open", observed_open)
    with pytest.raises(DiffSourceError, match="outside repository"):
        TestPilot(client, coverage=False).run(repo, DIFF)
    assert reads == []
    assert client.calls == []
    assert not events.exists()


def test_internal_source_link_in_read_only_directory_keeps_input_mode(tmp_path):
    repo, events = project(tmp_path)
    locked = repo / "locked"
    locked.mkdir()
    (locked / "alias.py").symlink_to("../values.py")
    locked.chmod(0o555)
    try:
        result = TestPilot(ScriptedModel(["Test amount.", generated(2)]),
                           max_repair_rounds=0, coverage=False).run(
                               repo, DIFF, targets=["locked/alias.py::amount", "values.py::amount"])
        assert result.status == "passed", result.final
        assert len(result.changed_functions) == 1
        assert result.changed_functions[0]["path"] == "locked/alias.py"
        assert [item["source"] for item in observations(events)] == [INITIAL, INITIAL]
        assert stat.S_IMODE(locked.stat().st_mode) == 0o555
        assert (locked / "alias.py").readlink() == Path("../values.py")
        assert (repo / "values.py").read_text() == INITIAL
    finally:
        # This is the authored fixture, restored so pytest can remove it.
        locked.chmod(0o755)
