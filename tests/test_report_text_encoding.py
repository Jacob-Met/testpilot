"""Native report/file receiving with authored data; no live model/provider calls."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from testpilot.loop import LoopResult, TestPilot, render_report, write_outputs
from testpilot.model import RoutingConfig, ScriptedModel
from testpilot.sandbox import coverage_available


def result_for(path="module.py", *, message="", status="failed"):
    return LoopResult(
        status=status,
        changed_functions=[{"path": path, "qualname": "measure"}],
        repair_rounds_used=0, max_repair_rounds=0,
        test_files={"tests/test_generated.py": "def test_generated():\n    assert True\n"},
        tests_written=1, final=None,
        patch="diff --git a/tests/test_generated.py b/tests/test_generated.py\n",
        coverage=None, ledger={"total_tokens": 0, "total_cost_usd": 0.0,
            "cost_is_complete": False, "tokens_estimated": False, "by_model": {}, "entries": []},
        rounds=[], message=message,
    )


def record(name, value):
    root = os.environ.get("TESTPILOT_REPORT_RECEIVING_EVIDENCE")
    if root:
        dest = Path(root); dest.mkdir(parents=True, exist_ok=True)
        (dest / (name + ".json")).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def test_filesystem_surrogate_is_visible_in_utf8_report_and_result_is_unchanged():
    path = os.fsdecode(b"module\xff.py")
    if "\udcff" not in path:
        pytest.skip("filesystem codec does not use the POSIX surrogateescape spelling")
    result = result_for(path)
    original = result.to_dict()
    text = render_report(result)
    encoded = text.encode("utf-8", errors="strict")
    assert "module\\udcff.py::measure" in encoded.decode("utf-8")
    assert result.to_dict() == original
    assert result.status == "failed" and result.ok is False


@pytest.mark.parametrize("field", ["message", "model"])
def test_nonfilesystem_surrogates_are_escaped_without_dropping_adjacent_unicode(field):
    result = result_for("café/雪.py")
    value = "before\ud800after café 雪 🙂"
    if field == "message":
        result.message = value
    else:
        result.ledger["by_model"][value] = {"calls": 1, "prompt_tokens": 3, "completion_tokens": 4}
    before = result.to_dict()
    text = render_report(result)
    text.encode("utf-8", errors="strict")
    assert "before\\ud800after café 雪 🙂" in text
    assert "café/雪.py::measure" in text
    assert result.to_dict() == before


def test_valid_unicode_and_literal_escape_text_are_preserved():
    message = "café 雪 🙂 and literal \\udcff are distinct from an undecodable byte"
    result = result_for("café/雪🙂.py", message=message)
    text = render_report(result)
    assert "café/雪🙂.py::measure" in text
    assert message in text
    assert "\\u00e9" not in text and "\\u96ea" not in text
    assert text.encode("utf-8").decode("utf-8") == text


def test_write_outputs_retains_json_identity_and_exact_patch_with_surrogate_path(tmp_path):
    result = result_for("module\udcff.py", message="runner failed; do not relabel this green")
    before = result.to_dict()
    paths = write_outputs(result, tmp_path / "outputs")
    assert paths["patch"].read_bytes() == result.patch.encode("utf-8")
    assert json.loads(paths["json"].read_text(encoding="utf-8")) == before
    markdown = paths["md"].read_bytes().decode("utf-8", errors="strict")
    assert "module\\udcff.py::measure" in markdown
    assert "# TestPilot report: **failed**" in markdown
    assert result.to_dict() == before


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def raw_filename_repo(tmp_path):
    repo = tmp_path / "repo"; repo.mkdir()
    filename = b"module\xff.py"
    path = repo / os.fsdecode(filename)
    path.write_bytes(b"def measure(value):\n    return value + 1\n")
    (repo / "tests").mkdir()
    old_test = repo / "tests/test_existing.py"
    old_test.write_bytes(b"def test_existing():\r\n    assert True\r\n")
    git(repo, "init", "-q")
    git(repo, "-c", "user.name=TestPilot fixture", "-c", "user.email=fixture@example.invalid",
        "add", ".")
    git(repo, "-c", "user.name=TestPilot fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-q", "-m", "authored fixture baseline")
    path.write_bytes(b"def measure(value):\n    return value + 2\n")
    diff = git(repo, "diff", "HEAD").stdout.decode("ascii")
    assert "\\377" in diff, "the actual Git diff must carry the raw filename byte"
    generated = (
        "import os\nimport runpy\n\n"
        "def test_measure_raw_filename():\n"
        f"    module = runpy.run_path(os.fsdecode(bytes.fromhex('{filename.hex()}')))\n"
        "    assert module['measure'](4) == 6\n"
    )
    response = "```python path=tests/test_raw_filename.py\n" + generated + "```\n"
    return repo, diff, ["Test the changed arithmetic through the real file.", response], {
        "module": path.read_bytes(), "existing_test": old_test.read_bytes(),
    }


@pytest.mark.skipif(os.name != "posix", reason="raw filename byte workflow requires POSIX")
def test_real_pytest_success_writes_complete_outputs_and_an_applicable_patch(tmp_path):
    repo, diff, responses, before = raw_filename_repo(tmp_path)
    pilot = TestPilot(ScriptedModel(responses), RoutingConfig(planner_model="P", editor_model="E"),
        max_repair_rounds=0, timeout_s=30, coverage=False)
    result = pilot.run(repo, diff)
    assert result.ok and result.final["passed"] == 2 and len(pilot.client.calls) == 2
    try:
        paths = write_outputs(result, tmp_path / "outputs")
    except UnicodeEncodeError as error:
        record("api-raw-filename", {"stage": "markdown_write_failed", "status": result.status,
            "final": result.final, "exception": str(error)})
        raise
    assert "module\\udcff.py::measure" in paths["md"].read_text(encoding="utf-8")
    assert json.loads(paths["json"].read_text())["changed_functions"][0]["path"] == "module\udcff.py"
    git(repo, "apply", "--check", str(paths["patch"]))
    git(repo, "apply", str(paths["patch"]))
    rerun = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=repo, capture_output=True, text=True, timeout=30)
    assert rerun.returncode == 0 and "2 passed" in rerun.stdout
    assert (repo / "module\udcff.py").read_bytes() == before["module"]
    assert (repo / "tests/test_existing.py").read_bytes() == before["existing_test"]
    record("api-raw-filename", {"stage": "complete", "status": result.status,
        "final": result.final, "patch_sha256": hashlib.sha256(paths["patch"].read_bytes()).hexdigest(),
        "receiving_pytest_stdout": rerun.stdout, "original_module_and_crlf_test_unchanged": True})


@pytest.mark.skipif(os.name != "posix" or not coverage_available(sys.executable),
    reason="raw filename CLI coverage workflow requires POSIX and coverage")
def test_real_cli_preserves_runner_failure_and_still_writes_readable_report(tmp_path):
    repo, diff, responses, before = raw_filename_repo(tmp_path)
    script = tmp_path / "script"; script.mkdir()
    for index, response in enumerate(responses):
        (script / f"{index:02d}.md").write_text(response, encoding="utf-8")
    patch_input = tmp_path / "change.diff"; patch_input.write_text(diff, encoding="ascii")
    output = tmp_path / "outputs"
    source_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=str(source_root), PYTHONDONTWRITEBYTECODE="1")
    for key in ["TESTPILOT_BACKEND", "TESTPILOT_PLANNER_MODEL", "TESTPILOT_EDITOR_MODEL", "TESTPILOT_PRICES"]:
        env.pop(key, None)
    run = subprocess.run([sys.executable, "-m", "testpilot", "run", "--repo", str(repo),
        "--diff", str(patch_input), "--backend", "scripted", "--script", str(script), "--rounds", "0",
        "--timeout", "30", "--out", str(output)], env=env, cwd=tmp_path,
        capture_output=True, text=True, timeout=60)
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    markdown = (output / "report.md").read_bytes()
    observed = {"returncode": run.returncode, "stdout": run.stdout, "stderr": run.stderr,
        "report_status": report["status"], "final": report["final"], "markdown_bytes": len(markdown)}
    record("cli-raw-filename", observed)
    # Coverage 7.16.2 rejects this filename in SQLite despite two passing cases.
    # Preserve the actual runner outcome; future coverage support may legitimately
    # make it pass, while report serialization must work in either outcome.
    expected_status = "passed" if report["final"]["returncode"] == 0 else "failed"
    assert report["status"] == expected_status
    assert run.returncode == (0 if expected_status == "passed" else 1)
    assert report["final"]["ok"] is (expected_status == "passed")
    assert report["final"]["passed"] == 2
    assert "UnicodeEncodeError" not in run.stderr
    assert f"# TestPilot report: **{expected_status}**" in run.stdout
    assert "module\\udcff.py::measure" in markdown.decode("utf-8", errors="strict")
    assert (repo / "module\udcff.py").read_bytes() == before["module"]
    assert (repo / "tests/test_existing.py").read_bytes() == before["existing_test"]
