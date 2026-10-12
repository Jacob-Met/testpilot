"""Reject invalid generation limits before inspecting inputs or starting work."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

from testpilot import __main__ as cli
from testpilot.loop import TestPilot
from testpilot.model import ScriptedModel


ROOT = Path(__file__).resolve().parents[1]
INVALID_LIMITS = [-1, -100, 0.5, 1.0, float("nan"), float("inf"), "1", True, False]


@pytest.mark.parametrize("name", ["max_repair_rounds", "max_total_tokens"])
@pytest.mark.parametrize("value", INVALID_LIMITS)
def test_api_rejects_invalid_limits_before_any_work(name, value):
    model = ScriptedModel([])
    with patch("testpilot.loop.run_pytest", side_effect=AssertionError("pytest must not start")):
        with pytest.raises(ValueError, match=rf"^{name} must be a nonnegative integer$"):
            TestPilot(model, **{name: value})
    assert model.calls == []


def test_api_keeps_zero_unlimited_budget_and_large_integer_limits():
    for rounds, budget in [(0, 0), (3, None), (10**30, 10**30)]:
        pilot = TestPilot(ScriptedModel([]), max_repair_rounds=rounds, max_total_tokens=budget)
        assert pilot.max_repair_rounds == rounds
        assert pilot.max_total_tokens == budget


@pytest.mark.parametrize("flag", ["--rounds", "--max-tokens"])
@pytest.mark.parametrize("value", ["-1", "-999999", "0.5", "nan", "infinity"])
def test_cli_rejects_invalid_limits_before_reading_inputs(flag, value, capsys):
    with (
        patch.object(cli, "_read_diff", side_effect=AssertionError("diff must not be read")),
        patch.object(cli, "make_client", side_effect=AssertionError("client must not be constructed")),
        patch.object(cli, "TestPilot", side_effect=AssertionError("generation must not start")),
        patch.object(cli, "write_outputs", side_effect=AssertionError("reports must not be written")),
    ):
        with pytest.raises(SystemExit) as caught:
            cli.main(["run", "--repo", "missing-project", "--diff", "missing.diff", f"{flag}={value}"])
    assert caught.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"argument {flag}:" in captured.err
    assert "nonnegative integer" in captured.err


@pytest.mark.parametrize("flag", ["--rounds", "--max-tokens"])
def test_actual_cli_preserves_existing_reports_on_negative_limits(tmp_path, flag):
    output = tmp_path / "existing-review"
    output.mkdir()
    prior = {}
    for name in ("report.json", "report.md", "report.html", "testpilot.patch"):
        data = f"previous review: {name}\n".encode()
        (output / name).write_bytes(data)
        prior[name] = data
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        [sys.executable, "-B", "-m", "testpilot", "run", "--repo", str(tmp_path / "absent-project"),
         "--diff", str(tmp_path / "absent.diff"), "--backend", "scripted", "--script",
         str(tmp_path / "absent-script"), "--out", str(output), f"{flag}=-1"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 2, result.stderr
    assert result.stdout == ""
    assert f"argument {flag}:" in result.stderr
    assert "nonnegative integer" in result.stderr
    assert "Traceback" not in result.stderr
    assert {path.name: path.read_bytes() for path in output.iterdir()} == prior


def test_actual_cli_keeps_zero_round_generation_and_zero_token_budget(tmp_path):
    repo = tmp_path / "project"
    repo.mkdir()
    (repo / "subject.py").write_text("def value():\n    return 7\n", encoding="utf-8")
    diff = tmp_path / "change.diff"
    diff.write_text("--- a/subject.py\n+++ b/subject.py\n@@ -1,2 +1,2 @@\n def value():\n"
                    "-    return 6\n+    return 7\n", encoding="utf-8")
    script = tmp_path / "script"
    script.mkdir()
    (script / "01.txt").write_text("Check the changed value.", encoding="utf-8")
    (script / "02.txt").write_text(
        "```python path=tests/test_value.py\nfrom subject import value\n\n"
        "def test_value():\n    assert value() == 7\n```\n", encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1")
    for name, limits, expected_status, expected_calls in [
        ("zero-rounds", ["--rounds", "0"], "passed", 2),
        ("zero-budget", ["--max-tokens", "0"], "budget_exhausted", 0),
    ]:
        output = tmp_path / name
        result = subprocess.run(
            [sys.executable, "-B", "-m", "testpilot", "run", "--repo", str(repo),
             "--diff", str(diff), "--backend", "scripted", "--script", str(script),
             "--no-coverage", "--timeout", "15", "--out", str(output), *limits],
            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == (0 if expected_status == "passed" else 1), result.stderr
        report = json.loads((output / "report.json").read_text(encoding="utf-8"))
        assert report["status"] == expected_status
        assert len(report["ledger"]["entries"]) == expected_calls
        assert report["repair_rounds_used"] == 0
        if expected_status == "passed":
            assert report["final"]["generated"]["passed"] == 1
    assert sorted(path.name for path in repo.iterdir()) == ["subject.py"]
    assert (repo / "subject.py").read_text(encoding="utf-8") == "def value():\n    return 7\n"
