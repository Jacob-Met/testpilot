"""Actual CLI admission and execution controls for run --timeout."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
INVALID_TIMEOUTS = ("nan", "NaN", "inf", "+inf", "-inf", "1e309", "0", "-0.0", "-1")

def _command(args):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, "-B", "-m", "testpilot", *args],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)

@pytest.mark.parametrize("value", INVALID_TIMEOUTS)
def test_run_refuses_invalid_timeout_before_touching_inputs_or_outputs(tmp_path, value):
    # None of these inputs exists. Timeout admission must precede their readers,
    # model construction, sandbox launch and publication.
    out = tmp_path / "out"
    out.mkdir()
    old = {}
    for name in ("report.json", "report.md", "report.html", "testpilot.patch"):
        raw = ("previous completed review: " + name).encode()
        (out / name).write_bytes(raw)
        old[name] = raw
    result = _command(["run", "--repo", str(tmp_path / "missing-repo"),
                       "--diff", str(tmp_path / "missing.diff"),
                       "--script", str(tmp_path / "missing-script"),
                       "--out", str(out), "--timeout=" + value])
    assert result.returncode == 2, result.stderr
    assert "positive finite" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout
    assert {p.name: p.read_bytes() for p in out.iterdir()} == old

@pytest.mark.parametrize("value", ("0.125", "6e1", "60"))
def test_run_accepts_finite_positive_timeout_without_changes(tmp_path, value):
    repo = tmp_path / "repo"
    repo.mkdir()
    diff = tmp_path / "empty.diff"
    diff.write_bytes(b"")
    script = tmp_path / "script"
    script.mkdir()
    (script / "01.txt").write_text("unused", encoding="utf-8")
    out = tmp_path / "out"
    result = _command(["run", "--repo", str(repo), "--diff", str(diff),
                       "--script", str(script), "--out", str(out), "--timeout=" + value])
    assert result.returncode == 1, result.stderr
    report = json.loads((out / "report.json").read_bytes())
    assert report["status"] == "no_changes"
    assert report["ledger"]["entries"] == []
    assert sorted(p.name for p in out.iterdir()) == [
        "report.html", "report.json", "report.md", "testpilot.patch"]

@pytest.mark.parametrize("timeout", (None, "60"))
def test_run_default_and_explicit_timeout_execute_real_scripted_pytest(tmp_path, timeout):
    case = ROOT / "eval" / "cases" / "stats_median"
    out = tmp_path / "result"
    args = ["run", "--repo", str(case / "repo"), "--diff", str(case / "change.diff"),
            "--script", str(case / "script"), "--out", str(out), "--no-coverage"]
    if timeout is not None:
        args.append("--timeout=" + timeout)
    result = _command(args)
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((out / "report.json").read_bytes())
    assert report["status"] == "passed"
    assert report["tests_written"] == 3
    assert report["final"]["timeout_s"] == 60.0
    assert len(report["ledger"]["entries"]) == 2
    assert report["final"]["junit_available"] is True
