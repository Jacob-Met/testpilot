"""Actual CLI and separate-dispatch receiving for saved report comparisons."""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

from test_compare import raw, sample


def test_compare_dispatch_never_calls_generator_model_or_sandbox(tmp_path, monkeypatch):
    from testpilot import __main__ as cli
    import testpilot.sandbox as sandbox
    def forbidden(*args, **kwargs):
        raise AssertionError("comparison executed a runner or model")
    monkeypatch.setattr(cli, "make_client", forbidden)
    monkeypatch.setattr(cli.TestPilot, "run", forbidden)
    monkeypatch.setattr(sandbox, "run_pytest", forbidden)
    before, after = tmp_path / "before.json", tmp_path / "after.json"
    before.write_bytes(raw())
    data = sample()
    data["status"] = "failed"
    after.write_bytes(raw(data))
    assert cli.main(["compare", "--before", str(before), "--after", str(after),
                     "--out", str(tmp_path / "comparison.html")]) == 0
    assert before.read_bytes() == raw()
    assert after.read_bytes() == raw(data)


def test_actual_cli_acceptance_refusal_and_optimized_admission(tmp_path):
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "PYTHONPATH": str(root), "PYTHONDONTWRITEBYTECODE": "1"}
    before, after = tmp_path / "before.json", tmp_path / "after.json"
    before.write_bytes(raw())
    after.write_bytes(raw())
    expected_hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in (before, after)]
    command = [sys.executable, "-B", "-m", "testpilot", "compare",
               "--before", str(before), "--after", str(after)]
    output = tmp_path / "comparison.html"
    result = subprocess.run(command + ["--out", str(output)], cwd=root, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    original = output.read_bytes()
    result = subprocess.run(command + ["--out", str(output)], cwd=root, env=env, capture_output=True, text=True)
    assert result.returncode == 2 and output.read_bytes() == original
    assert "cannot compare" in result.stderr
    after.write_bytes(raw().replace(b'"tests_written": 1', b'"tests_written": true'))
    malformed = tmp_path / "malformed.html"
    optimized = [sys.executable, "-O", "-B", "-m", "testpilot", "compare",
                 "--before", str(before), "--after", str(after), "--out", str(malformed)]
    result = subprocess.run(optimized, cwd=root, env=env, capture_output=True, text=True)
    assert result.returncode == 2 and not malformed.exists()
    assert "tests_written" in result.stderr
    after.write_bytes(raw())
    assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in (before, after)] == expected_hashes
