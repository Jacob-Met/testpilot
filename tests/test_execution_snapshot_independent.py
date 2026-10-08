"""Independent hosted receiving for captured-source custody and read-only inputs.

Frozen source controls execute against this checkout's unchanged dependencies.
This module creates only its own pytest fixtures.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import traceback

import pytest

import testpilot.loop as current_loop
import testpilot.snapshot as current_snapshot
from testpilot.model import ScriptedModel

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "docs/receiving/execution-snapshot-f5c43297f890/independent"
INITIAL = "def amount():\n    return 2\n"
DIFF = ("--- a/values.py\n+++ b/values.py\n@@ -1,2 +1,2 @@\n"
        " def amount():\n-    return 1\n+    return 2\n")
REPLY = ("```python path=tests/test_probe.py\n"
         "from values import amount\n\ndef test_probe():\n    assert amount() == 2\n"
         "```\n")
TARGETS = ["locked/alias.py::amount", "values.py::amount"]
pytestmark = pytest.mark.skipif(
    os.name != "posix" or not hasattr(os, "geteuid") or os.geteuid() == 0,
    reason="Requires an unprivileged POSIX account to qualify real directory permissions.",
)


def _load_control(filename, expected, name, monkeypatch):
    source = CONTROL / filename
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
    spec = importlib.util.spec_from_file_location("testpilot." + name, source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


def _fixture(tmp_path, *, ignored_target=False, readonly_root=False):
    repo = tmp_path / "project"
    (repo / "tests").mkdir(parents=True)
    (repo / "locked").mkdir()
    if ignored_target:
        (repo / ".venv").mkdir()
        (repo / ".venv/values.py").write_text(INITIAL, encoding="utf-8")
        (repo / "values.py").symlink_to(".venv/values.py")
    else:
        (repo / "values.py").write_text(INITIAL, encoding="utf-8")
    (repo / "locked/alias.py").symlink_to("../values.py")
    (repo / "tests/test_existing.py").write_text(
        "from values import amount\n\ndef test_existing():\n    assert amount() == 2\n",
        encoding="utf-8",
    )
    events = tmp_path / "phases.jsonl"
    hook = (
        "from pathlib import Path\nimport json\nimport stat\n\n"
        "def pytest_sessionstart(session):\n"
        "    root = Path(__file__).parent\n"
        "    row = {'source': (root / 'values.py').read_text(), 'root': str(root),\n"
        "           'generated': bool(list((root / 'tests').glob('test_probe*.py'))),\n"
        "           'locked_mode': stat.S_IMODE((root / 'locked').stat().st_mode),\n"
        "           'root_mode': stat.S_IMODE(root.stat().st_mode)}\n"
        f"    with Path({str(events)!r}).open('a', encoding='utf-8') as stream:\n"
        "        stream.write(json.dumps(row) + '\\n')\n"
    )
    (repo / "conftest.py").write_text(hook, encoding="utf-8")
    (repo / "locked").chmod(0o555)
    if ignored_target:
        (repo / ".venv").chmod(0o555)
    if readonly_root:
        repo.chmod(0o555)
    return repo, events


def _caller_identity(repo):
    return {
        "source": (repo / "values.py").read_bytes(),
        "alias": (repo / "locked/alias.py").readlink(),
        "locked_mode": stat.S_IMODE((repo / "locked").stat().st_mode),
        "root_mode": stat.S_IMODE(repo.stat().st_mode),
        "source_link": (repo / "values.py").readlink() if (repo / "values.py").is_symlink() else None,
        "ignored_mode": stat.S_IMODE((repo / ".venv").stat().st_mode) if (repo / ".venv").exists() else None,
    }


def _restore_fixture_modes(repo):
    # Exclusively owned test directories, after all custody assertions.
    for directory in (repo, repo / "locked", repo / ".venv"):
        if directory.exists() and not directory.is_symlink():
            directory.chmod(stat.S_IMODE(directory.stat().st_mode) | stat.S_IRWXU)


def _assert_success(result, client, events, original):
    assert result.status == "passed", result.to_dict()
    assert len(result.changed_functions) == 1
    selected = result.changed_functions[0]
    assert selected["path"] == TARGETS[0].split("::")[0]
    assert selected["source"] == INITIAL.rstrip("\n")
    assert selected["changed_lines"] == [2]
    assert len(result.ledger["entries"]) == 2
    assert len(client.calls) == 2
    assert result.final["generated"]["passed"] == 1
    rows = [json.loads(line) for line in events.read_text().splitlines()]
    assert len(rows) == 2
    assert [row["source"] for row in rows] == [INITIAL, INITIAL]
    assert [row["generated"] for row in rows] == [False, True]
    assert len({row["root"] for row in rows}) == 2
    assert all(row["locked_mode"] == original["locked_mode"] for row in rows)
    assert all(row["root_mode"] == original["root_mode"] for row in rows)
    return rows


@pytest.mark.parametrize("variant", ["current-baseline", "first-candidate", "corrected-candidate"])
def test_readonly_alias_has_healthy_original_and_discriminating_candidate_controls(
    tmp_path, monkeypatch, variant
):
    repo, events = _fixture(tmp_path)
    original = _caller_identity(repo)
    client = ScriptedModel(["Pin the captured amount.", REPLY])
    pilot_type = current_loop.TestPilot
    if variant == "current-baseline":
        module = _load_control(
            "baseline_loop.py",
            "7e2336ff4d3e88aa8f575e4d7c04f3fe1cc1bf3023f0d230941ab63cead675a8",
            "_receiving_baseline_loop", monkeypatch,
        )
        pilot_type = module.TestPilot
    elif variant == "first-candidate":
        module = _load_control(
            "first_snapshot.py",
            "ec1ab4df0b92727defc176d04b1df771aa677195bec0f5502cc62e8d7091f1a3",
            "_receiving_first_snapshot", monkeypatch,
        )
        monkeypatch.setattr(current_loop, "capture_project", module.capture_project)
    try:
        pilot = pilot_type(client, max_repair_rounds=0, timeout_s=15, coverage=False)
        if variant == "first-candidate":
            with pytest.raises(PermissionError) as raised:
                pilot.run(repo, DIFF, targets=TARGETS)
            assert any(frame.name == "rebind" for frame in traceback.extract_tb(raised.value.__traceback__))
            assert client.calls == []
            assert not events.exists()
        else:
            result = pilot.run(repo, DIFF, targets=TARGETS)
            _assert_success(result, client, events, original)
        assert _caller_identity(repo) == original
    finally:
        _restore_fixture_modes(repo)


def test_readonly_root_can_capture_internal_alias_to_ignored_source(tmp_path):
    repo, events = _fixture(tmp_path, ignored_target=True, readonly_root=True)
    original = _caller_identity(repo)
    client = ScriptedModel(["Pin the captured amount.", REPLY])
    try:
        result = current_loop.TestPilot(
            client, max_repair_rounds=0, timeout_s=15, coverage=False
        ).run(repo, DIFF, targets=TARGETS)
        _assert_success(result, client, events, original)
        assert _caller_identity(repo) == original
    finally:
        _restore_fixture_modes(repo)


@pytest.mark.parametrize("inject_failure", [False, True], ids=["success", "link-recreation-error"])
def test_private_copy_modes_are_restored_and_caller_modes_are_never_changed(
    tmp_path, monkeypatch, inject_failure
):
    repo, _ = _fixture(tmp_path)
    original = _caller_identity(repo)
    view = tmp_path / "owned-selection-view"
    real_chmod = Path.chmod
    real_symlink = Path.symlink_to
    changes = []
    fault_modes = []

    def observed_chmod(directory, mode, *args, **kwargs):
        changes.append({
            "inside": directory.resolve().is_relative_to(view),
            "symlink": directory.is_symlink(),
            "mode": mode,
        })
        return real_chmod(directory, mode, *args, **kwargs)

    def controlled_symlink(link, target, *args, **kwargs):
        if inject_failure and link.name == "alias.py" and link.is_relative_to(view):
            fault_modes.append(stat.S_IMODE(link.parent.stat().st_mode))
            raise OSError("authored private link recreation failure")
        return real_symlink(link, target, *args, **kwargs)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(Path, "chmod", observed_chmod)
            patch.setattr(Path, "symlink_to", controlled_symlink)
            if inject_failure:
                with pytest.raises(OSError, match="authored private link recreation failure"):
                    current_snapshot._selection_view(repo, view, ["locked/alias.py", "values.py"])
            else:
                current_snapshot._selection_view(repo, view, ["locked/alias.py", "values.py"])
        assert changes
        assert all(item["inside"] and not item["symlink"] for item in changes)
        assert stat.S_IMODE((view / "locked").stat().st_mode) == 0o555
        assert stat.S_IMODE(view.stat().st_mode) == original["root_mode"]
        assert _caller_identity(repo) == original
        if inject_failure:
            assert fault_modes == [0o755]
        else:
            assert (view / "locked/alias.py").is_symlink()
            assert (view / "locked/alias.py").resolve() == view / "values.py"
    finally:
        _restore_fixture_modes(repo)
        if view.exists():
            _restore_fixture_modes(view)


@pytest.mark.parametrize("new_path", ["tests/test_probe.py", "checks/test_probe.py"])
def test_new_live_caller_paths_and_module_names_remain_reserved_after_capture(
    tmp_path, new_path
):
    repo, events = _fixture(tmp_path)
    original = _caller_identity(repo)
    added = repo / new_path
    retained = "def test_caller_added_later():\n    assert True\n"
    calls = 0

    def response(model, messages):
        nonlocal calls
        calls += 1
        if calls == 1:
            added.parent.mkdir(exist_ok=True)
            added.write_text(retained, encoding="utf-8")
            return "Pin the captured amount."
        return REPLY

    client = ScriptedModel(response)
    try:
        result = current_loop.TestPilot(
            client, max_repair_rounds=0, timeout_s=15, coverage=False
        ).run(repo, DIFF, targets=TARGETS)
        _assert_success(result, client, events, original)
        assert set(result.test_files) == {"tests/test_probe_testpilot.py"}
        assert added.read_text(encoding="utf-8") == retained
        assert "\n+++ b/tests/test_probe_testpilot.py\n" in result.patch
        assert "test_caller_added_later" not in result.patch
        assert _caller_identity(repo) == original
    finally:
        _restore_fixture_modes(repo)


def test_actual_cli_and_emitted_patch_share_the_captured_source(tmp_path):
    driver = ROOT / "docs/receiving/execution-snapshot-f5c43297f890/receive_snapshot_cli.py"
    assert hashlib.sha256(driver.read_bytes()).hexdigest() == (
        "244f95db22e087a4e595d46808bf5f2f8c2861ae6f1256330d8d26f9e191ec7e"
    )
    destination = tmp_path / "actual-cli-receiving"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["TESTPILOT_BACKEND"] = "scripted"
    executed = subprocess.run(
        [sys.executable, "-B", str(driver), str(ROOT), str(destination)],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=180,
    )
    assert executed.returncode == 0, executed.stdout + executed.stderr
    receipt = json.loads((destination / "receipt.json").read_bytes())
    assert receipt["schema"] == "hamon.testpilot_execution_snapshot.cli_receiving.v1"
    assert receipt["source_unchanged"] is True
    actual_pins = {
        source.relative_to(ROOT).as_posix(): hashlib.sha256(source.read_bytes()).hexdigest()
        for source in sorted((ROOT / "testpilot").glob("*.py"))
    }
    assert receipt["source_before"] == receipt["source_after"] == actual_pins
    assert receipt["source_base"] == subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    expected = {
        "misleading_success": ("failed", 1, 1),
        "keep_initial_checkout": ("passed", 0, 0),
        "unchanged_control": ("passed", 0, 0),
    }
    assert [row["case"] for row in receipt["cases"]] == list(expected)
    for row in receipt["cases"]:
        status, cli_code, patch_code = expected[row["case"]]
        assert row["status"] == status, row
        assert row["returncode"] == cli_code
        assert row["patch_pytest_on_captured_checkout_returncode"] == patch_code
        assert row["patch_applies_to_captured_checkout"] is True
        assert row["caller_source_expected_preserved"] is True
        assert row["recorded_selected_source"] == INITIAL.rstrip("\n")
        assert row["ledger_entries"] == 2
        assert row["final"]["returncode"] == patch_code
        assert row["final"]["timed_out"] is False
        assert row["oracles"] == {
            "baseline_and_generation_share_initial_source": True,
            "recorded_success_matches_captured_checkout": True,
            "ordinary_caller_edit_preserved": True,
        }
        phases = row["pytest_phase_events"]
        assert [phase["source"] for phase in phases] == [INITIAL, INITIAL]
        assert [phase["generated_present"] for phase in phases] == [False, True]
