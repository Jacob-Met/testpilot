"""Actual pytest/CLI consumers: a green existing suite cannot qualify an unrun patch."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from testpilot.loop import TestPilot, count_tests
from testpilot.model import ScriptedModel
from testpilot.sandbox import run_pytest

SOURCE = "def normalize(text):\n    return text.strip().lower()\n"
DIFF = "--- /dev/null\n+++ b/normalizer.py\n@@ -0,0 +1,2 @@\n" + "".join(
    "+" + line + "\n" for line in SOURCE.splitlines()
)
GOOD = ('from normalizer import normalize\n\ndef test_generated():\n'
        '    assert normalize(" Keep ") == "keep"\n')
BAD = GOOD.replace('== "keep"', '== "INTENTIONAL_FAILURE"')
GENERATED = "tests/test_generated.py"


def project(tmp_path, *, testpaths="checks", extra_config=""):
    repo = tmp_path / "project source"
    (repo / "checks").mkdir(parents=True)
    (repo / "normalizer.py").write_text(SOURCE)
    (repo / "checks/test_existing.py").write_text(
        'from normalizer import normalize\n\ndef test_existing():\n'
        '    assert normalize(" Existing ") == "existing"\n'
    )
    config = "[tool.pytest.ini_options]\n"
    if testpaths is not None:
        config += "testpaths = " + json.dumps([testpaths]) + "\n"
    (repo / "pyproject.toml").write_text(config + extra_config)
    return repo


def snapshots(repo):
    return {p.relative_to(repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in repo.rglob("*") if p.is_file()}


def reply(code, path=GENERATED):
    return f"```python path={path}\n{code}```\n"


def generate(repo, code=GOOD, *, repairs=()):
    client = ScriptedModel(["Check normalization.", reply(code), *repairs])
    result = TestPilot(client, coverage=False, timeout_s=15,
                       max_repair_rounds=len(repairs)).run(repo, DIFF)
    return result, client


def test_configured_suite_and_generated_failure_are_both_executed(tmp_path):
    repo = project(tmp_path)
    before = snapshots(repo)
    result, _ = generate(repo, BAD)
    assert not result.ok and result.status == "failed"
    assert result.final["passed"] == 1 and result.final["failed"] == 1
    assert result.tests_written == 1
    assert "INTENTIONAL_FAILURE" in result.final["output"]
    assert snapshots(repo) == before


def test_configured_roots_and_project_hooks_are_preserved(tmp_path):
    repo = project(tmp_path)
    (repo / "historical").mkdir()
    (repo / "historical/test_ambient.py").write_text("raise AssertionError('outside configured suite')\n")
    (repo / "conftest.py").write_text(
        'import pytest\n\n@pytest.fixture\ndef project_value():\n    return 42\n\n'
        'def pytest_collection_modifyitems(config, items):\n'
        '    removed = [item for item in items if item.name == "test_filtered"]\n'
        '    items[:] = [item for item in items if item not in removed]\n'
        '    config.hook.pytest_deselected(items=removed)\n'
    )
    generated = ('def test_generated(project_value):\n    assert project_value == 42\n\n'
                 'def test_filtered():\n    raise AssertionError("hook must retain selection")\n')
    before = snapshots(repo)
    result, _ = generate(repo, generated)
    assert result.ok and result.final["passed"] == 2
    assert result.tests_written == 1
    assert "outside configured suite" not in result.final["output"]
    assert snapshots(repo) == before


def test_generated_file_runs_once_when_normal_discovery_already_covers_it(tmp_path):
    repo = project(tmp_path, testpaths=None)
    generated = ('seen = set()\n\ndef test_generated_once():\n'
                 '    assert not seen\n    seen.add("executed")\n')
    result, _ = generate(repo, generated)
    assert result.ok and result.final["passed"] == 2
    assert result.tests_written == 1


def test_existing_failure_stays_visible_beside_passing_generated_test(tmp_path):
    repo = project(tmp_path)
    (repo / "checks/test_existing.py").write_text('def test_existing():\n    assert False, "existing failure"\n')
    result, _ = generate(repo)
    assert not result.ok and result.status == "failed"
    assert result.final["failed"] == 1 and result.final["passed"] == 1
    assert result.tests_written == 1
    assert "existing failure" in result.final["output"]


@pytest.mark.parametrize("generated", [
    "helper_value = 42\n",
    'import pytest\n\n@pytest.mark.skip(reason="not executed")\ndef test_generated():\n    assert False\n',
    'import pytest\npytest.skip("module not executed", allow_module_level=True)\n',
])
def test_existing_passes_do_not_qualify_helper_only_or_skipped_output(tmp_path, generated):
    repo = project(tmp_path)
    result, _ = generate(repo, generated)
    assert not result.ok and result.status == "no_tests"
    assert result.final["passed"] == 1 and result.final["returncode"] == 0
    assert "no generated test case passed" in result.message
    assert result.patch


def test_keyword_deselection_is_respected_and_cannot_qualify_generated_output(tmp_path):
    repo = project(tmp_path)
    result = run_pytest(repo, {GENERATED: GOOD}, coverage=False, timeout=15,
                        pytest_args=("-k", "existing"))
    assert not result.ok and result.returncode == 0 and result.passed == 1
    assert result.junit_available and count_tests({GENERATED: GOOD}, result, set()) == 0
    assert "No generated test case passed" in result.failure_report()


@pytest.mark.parametrize("body", ["while True:\n        pass", "__import__('os')._exit(3)"])
def test_missing_junit_preserves_written_count_without_qualifying_execution(tmp_path, body):
    repo = project(tmp_path)
    generated = (f"def test_incomplete():\n    {body}\n\n"
                 "def test_unreached():\n    assert True\n")
    client = ScriptedModel(["Check normalization.", reply(generated)])
    result = TestPilot(client, coverage=False, timeout_s=1,
                       max_repair_rounds=0).run(repo, DIFF)
    assert not result.ok and result.status == "failed"
    assert result.tests_written == 2 and result.final["junit_available"] is False
    assert result.final["generated"]["collected"] == 0
    assert result.final["generated"]["passed"] == 0


def test_complete_empty_junit_does_not_fall_back_to_static_definitions(tmp_path):
    repo = project(tmp_path)
    result = run_pytest(repo, {GENERATED: GOOD}, coverage=False, timeout=15,
                        pytest_args=("-k", "no_such_test_name"))
    assert not result.ok and result.returncode == 5 and result.junit_available
    assert not result.cases and count_tests({GENERATED: GOOD}, result, set()) == 0


def test_parameterized_counts_use_file_provenance_with_junit_prefix(tmp_path):
    repo = project(tmp_path)
    generated = ('import pytest\n\n'
                 '@pytest.mark.parametrize("value", [1, 2, 3], ids=["a::b", "c/d", "normal"])\n'
                 'def test_generated(value):\n    assert value > 0\n')
    result = run_pytest(repo, {GENERATED: generated}, coverage=False, timeout=15,
                        pytest_args=("--junit-prefix=custom.project",))
    assert result.ok and result.passed == 4
    assert len(result.generated_cases) == 3
    assert all(case.nodeid.startswith("custom.project.") for case in result.cases)


def test_helper_file_and_skipped_case_are_allowed_beside_passing_generated_case(tmp_path):
    repo = project(tmp_path)
    generated = ('import pytest\n\ndef test_generated():\n    assert True\n\n'
                 '@pytest.mark.skip(reason="optional case")\ndef test_optional():\n    assert False\n')
    result = run_pytest(repo, {GENERATED: generated, "tests/test_helpers.py": "helper_value = 42\n"},
                        coverage=False, timeout=15)
    assert result.ok and result.passed == 2 and result.skipped == 1
    assert len(result.generated_cases) == 2


def test_empty_generation_gets_actionable_repair_and_new_test_is_really_run(tmp_path):
    repo = project(tmp_path)
    result, client = generate(repo, "helper_value = 42\n", repairs=[reply(GOOD)])
    assert result.ok and result.repair_rounds_used == 1 and result.tests_written == 1
    assert result.rounds[0].result["ok"] is False
    assert result.final["passed"] == 2
    assert "No generated test case passed" in client.calls[2][1][1]["content"]


def test_cli_patch_receiving_matches_the_reported_generated_execution(tmp_path):
    repo = project(tmp_path)
    (tmp_path / "change.diff").write_text(DIFF)
    script = tmp_path / "scripted replies"
    script.mkdir()
    (script / "01_plan.md").write_text("Check normalization.")
    (script / "02_tests.md").write_text(reply(BAD))
    out = tmp_path / "output"
    before = snapshots(repo)
    env = {k: v for k, v in os.environ.items() if not k.startswith("TESTPILOT_")}
    env.update(PYTHONPATH=str(Path(__file__).resolve().parents[1]), PYTHONDONTWRITEBYTECODE="1")
    command = [sys.executable, "-B", "-m", "testpilot", "run", "--repo", str(repo),
               "--diff", str(tmp_path / "change.diff"), "--backend", "scripted", "--script", str(script),
               "--rounds", "0", "--timeout", "15", "--out", str(out)]
    process = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=45,
                             check=False)
    report = json.loads((out / "report.json").read_text())
    assert process.returncode == 1 and report["status"] == "failed", process.stdout + process.stderr
    assert report["tests_written"] == 1 and report["final"]["failed"] == 1
    assert snapshots(repo) == before
    consumer = tmp_path / "patch consumer"
    shutil.copytree(repo, consumer)
    subprocess.run(["git", "apply", str(out / "testpilot.patch")], cwd=consumer, check=True, capture_output=True)
    rerun = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "checks", GENERATED], cwd=consumer,
                           env={**env, "PYTHONPATH": str(consumer)}, capture_output=True, text=True, timeout=30,
                           check=False)
    assert rerun.returncode == 1 and "1 failed, 1 passed" in rerun.stdout
    assert "INTENTIONAL_FAILURE" in rerun.stdout
