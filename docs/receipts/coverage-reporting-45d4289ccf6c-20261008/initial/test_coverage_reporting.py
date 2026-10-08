"""Configured coverage-report receiving through the actual installed tools."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

pytest.importorskip("coverage")
from testpilot.sandbox import run_pytest

CODE = 'def classify(value):\n    if value >= 0:\n        return "nonnegative"\n    return "negative"\n'
EXISTING = 'from calc import classify\n\ndef test_nonnegative():\n    assert classify(1) == "nonnegative"\n'

def make_project(root: Path, *, threshold: int = 100, test: str = EXISTING) -> Path:
    repo = root / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "calc.py").write_text(CODE)
    (repo / ".coveragerc").write_text(f"[report]\nfail_under = {threshold}\n")
    (repo / "tests/test_existing.py").write_text(test)
    return repo

def source_bytes(repo: Path) -> dict[str, bytes]:
    return {str(p.relative_to(repo)): p.read_bytes() for p in repo.rglob("*") if p.is_file()}

@pytest.mark.parametrize("threshold", [0, 100])
def test_partial_report_preserves_measured_lines_below_threshold(tmp_path, threshold):
    repo = make_project(tmp_path, threshold=threshold)
    before = source_bytes(repo)
    result = run_pytest(repo, timeout=30, coverage=True)
    assert result.ok and result.passed == 1
    assert result.coverage is not None
    assert result.coverage.percent_total == 75.0
    assert result.coverage.executed("calc.py") == {1, 2, 3}
    assert result.coverage.executable("calc.py") == {1, 2, 3, 4}
    assert source_bytes(repo) == before

def test_measured_zero_retains_its_executable_population(tmp_path):
    repo = make_project(tmp_path, test="def test_control():\n    assert True\n")
    before = source_bytes(repo)
    result = run_pytest(repo, timeout=30, coverage=True)
    assert result.ok and result.passed == 1
    assert result.coverage is not None
    assert result.coverage.percent_total == 0.0
    assert result.coverage.executed("calc.py") == set()
    assert result.coverage.executable("calc.py") == {1, 2, 3, 4}
    assert source_bytes(repo) == before

def test_failed_collection_is_unavailable_while_test_outcome_survives(tmp_path):
    test = ('import calc\nfrom pathlib import Path\n\ndef test_remove_temporary_source():\n'
            '    assert calc.classify(1) == "nonnegative"\n'
            '    Path(calc.__file__).unlink()\n')
    repo = make_project(tmp_path, test=test)
    before = source_bytes(repo)
    result = run_pytest(repo, timeout=30, coverage=True)
    assert result.ok and result.passed == 1 and result.returncode == 0
    assert result.coverage is None
    assert source_bytes(repo) == before

def test_below_threshold_measurement_does_not_hide_failed_tests(tmp_path):
    repo = make_project(tmp_path, test=EXISTING.replace('"nonnegative"', '"wrong"'))
    before = source_bytes(repo)
    result = run_pytest(repo, timeout=30, coverage=True)
    assert not result.ok and result.failed == 1 and result.returncode == 1
    assert result.coverage is not None
    assert result.coverage.percent_total == 75.0
    assert source_bytes(repo) == before

def test_public_cli_keeps_reports_when_final_collection_is_unavailable(tmp_path):
    repo = make_project(tmp_path)
    before = source_bytes(repo)
    diff = tmp_path / "change.diff"
    diff.write_text('diff --git a/calc.py b/calc.py\n--- a/calc.py\n+++ b/calc.py\n'
                    '@@ -1,4 +1,4 @@\n def classify(value):\n     if value >= 0:\n'
                    '-        return "positive"\n+        return "nonnegative"\n'
                    '     return "negative"\n')
    script = tmp_path / "script"; script.mkdir()
    (script/"01_plan.md").write_text("Check the negative branch.\n")
    (script/"02_tests.md").write_text(
        '```python path=tests/test_negative.py\nimport calc\nfrom pathlib import Path\n\n'
        'def test_negative():\n    assert calc.classify(-1) == "negative"\n'
        '    Path(calc.__file__).unlink()\n```\n')
    out = tmp_path/"output"
    env = dict(os.environ)
    for name in list(env):
        if name.startswith("TESTPILOT_"):
            env.pop(name)
    source = Path(__import__("testpilot").__file__).resolve().parent.parent
    env.update(PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    run = subprocess.run(
        [sys.executable, "-m", "testpilot", "run", "--repo", str(repo), "--diff", str(diff),
         "--backend", "scripted", "--script", str(script), "--rounds", "0", "--timeout", "30",
         "--out", str(out)], env=env, cwd=tmp_path, capture_output=True, text=True, timeout=90)
    assert run.returncode == 0, (run.stdout, run.stderr)
    report = json.loads((out/"report.json").read_text())
    assert report["status"] == "passed"
    assert report["final"]["passed"] == 2
    assert report["final"]["coverage"] is None
    assert report["coverage"] is None
    markdown = (out/"report.md").read_text()
    assert "- Coverage: unavailable\n" in markdown
    assert "Coverage (total)" not in markdown
    assert "install `coverage`" not in markdown
    assert "new file mode 100644" in (out/"testpilot.patch").read_text()
    assert source_bytes(repo) == before
