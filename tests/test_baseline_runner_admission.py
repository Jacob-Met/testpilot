"""An unavailable baseline must not consume generation or repair calls."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import venv

from testpilot import sandbox
from testpilot.loop import TestPilot
from testpilot.model import ScriptedModel
from testpilot.sandbox import CaseResult, CoverageReport, SandboxResult


SOURCE = "def add(a, b):\n    return a + b\n"
DIFF = (
    "diff --git a/calc.py b/calc.py\n--- a/calc.py\n+++ b/calc.py\n"
    "@@ -1,2 +1,2 @@\n def add(a, b):\n-    return a - b\n+    return a + b\n"
)
GENERATED = (
    "```python path=tests/test_add.py\nfrom calc import add\n"
    "def test_add():\n    assert add(2, 3) == 5\n```\n"
)
PACKAGE_ROOT = Path(sandbox.__file__).resolve().parent.parent


def native_result(returncode=0, *, available=True, timed_out=False, cases=()):
    return SandboxResult(
        returncode, timed_out, 0.1, 5.0, "retained baseline diagnostics\n",
        cases=list(cases), junit_available=available,
    )


class _ProjectFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="testpilot-baseline-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        (self.repo / "calc.py").write_text(SOURCE, encoding="utf-8")

    def make_pilot(self, **kwargs):
        model = ScriptedModel(["Test addition.", GENERATED])
        return TestPilot(model, max_repair_rounds=0, coverage=False, **kwargs), model


class BaselineAdmissionTests(_ProjectFixture, unittest.TestCase):
    def test_unavailable_baseline_stops_before_any_model_call(self):
        for rc, timed_out in ((1, False), (0, False), (5, False), (None, True)):
            with self.subTest(returncode=rc, timed_out=timed_out):
                pilot, model = self.make_pilot()
                baseline = native_result(rc, available=False, timed_out=timed_out)
                with patch.object(pilot, "_run", return_value=baseline) as run:
                    result = pilot.run(self.repo, DIFF)
                self.assertEqual(result.status, "failed")
                self.assertIn("complete test report", result.message)
                self.assertEqual(model.calls, [])
                self.assertEqual(run.call_count, 1)
                self.assertEqual(result.final, baseline.to_dict())
                self.assertEqual(result.ledger["entries"], [])
                self.assertEqual(result.test_files, {})
                self.assertEqual(result.patch, "")
                self.assertEqual(result.rounds, [])
                self.assertEqual((self.repo / "calc.py").read_text(), SOURCE)

    def test_failed_or_empty_complete_baseline_still_generates(self):
        for rc, initial_cases in (
            (0, [CaseResult("old::test_ok", "passed")]),
            (1, [CaseResult("old::test_bad", "failed", "existing failure")]),
            (5, []),
        ):
            with self.subTest(returncode=rc):
                pilot, model = self.make_pilot()
                baseline = native_result(rc, cases=initial_cases)
                final_cases = [*initial_cases,
                               CaseResult("test_add::test_add", "passed",
                                          generated_file="tests/test_add.py")]
                final = native_result(1 if rc == 1 else 0, cases=final_cases)
                final.generated_files = ["tests/test_add.py"]
                with patch.object(pilot, "_run", side_effect=[baseline, final]) as run:
                    result = pilot.run(self.repo, DIFF)
                self.assertEqual(len(model.calls), 2)
                self.assertEqual(run.call_count, 2)
                self.assertEqual(result.status, "failed" if rc == 1 else "passed")
                self.assertEqual(list(result.test_files), ["tests/test_add.py"])
                self.assertFalse((self.repo / "tests/test_add.py").exists())

    def test_unavailable_baseline_does_not_compare_coverage_to_itself(self):
        pilot, model = self.make_pilot()
        baseline = native_result(1, available=False)
        baseline.coverage = CoverageReport(50.0, {"calc.py": {"executed": [1], "missing": [2]}})
        with patch.object(pilot, "_run", return_value=baseline):
            result = pilot.run(self.repo, DIFF)
        self.assertEqual(model.calls, [])
        self.assertIsNone(result.coverage)
        self.assertEqual(result.final["coverage"], baseline.to_dict()["coverage"])

    def test_existing_selected_usage_refusal_keeps_its_message(self):
        pilot, model = self.make_pilot(pytest_k="bad and (")
        baseline = native_result(4, available=False)
        with patch.object(pilot, "_run", return_value=baseline):
            result = pilot.run(self.repo, DIFF)
        self.assertEqual(result.message,
                         "pytest refused the selected baseline run; inspect its diagnostics")
        self.assertEqual(model.calls, [])
        self.assertIsNone(result.coverage)

    def test_no_source_changes_still_skip_runner_and_model(self):
        pilot, model = self.make_pilot()
        with patch.object(pilot, "_run", side_effect=AssertionError("unexpected runner")):
            result = pilot.run(self.repo, "")
        self.assertEqual(result.status, "no_changes")
        self.assertEqual(model.calls, [])


class MissingPytestNativeTests(_ProjectFixture, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.environment = tempfile.TemporaryDirectory(prefix="testpilot-no-pytest-")
        cls.addClassCleanup(cls.environment.cleanup)
        env_root = Path(cls.environment.name) / "venv"
        venv.EnvBuilder(with_pip=False, system_site_packages=False,
                        symlinks=os.name != "nt").create(env_root)
        cls.python = str(env_root / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))

    def test_real_missing_pytest_preserves_native_error_without_model_calls(self):
        pilot, model = self.make_pilot(python=self.python)
        result = pilot.run(self.repo, DIFF)
        self.assertEqual(result.status, "failed")
        self.assertIn("complete test report", result.message)
        self.assertEqual(model.calls, [])
        self.assertEqual(result.final["returncode"], 1)
        self.assertFalse(result.final["junit_available"])
        self.assertIn("No module named pytest", result.final["output"])
        self.assertEqual(result.ledger["total_tokens"], 0)
        self.assertEqual(result.test_files, {})
        self.assertEqual((self.repo / "calc.py").read_text(), SOURCE)

    def test_real_cli_saves_zero_call_failure_and_original_runner_diagnostics(self):
        diff = self.root / "change.diff"
        diff.write_text(DIFF, encoding="utf-8")
        script = self.root / "script"
        script.mkdir()
        (script / "01_plan.md").write_text("Test addition.\n", encoding="utf-8")
        (script / "02_tests.md").write_text(GENERATED, encoding="utf-8")
        output = self.root / "out"
        env = {k: v for k, v in os.environ.items() if not k.startswith("TESTPILOT_")}
        env.update(PYTHONPATH=str(PACKAGE_ROOT), PYTHONDONTWRITEBYTECODE="1")
        run = subprocess.run(
            [sys.executable, "-m", "testpilot", "run", "--repo", str(self.repo),
             "--diff", str(diff), "--backend", "scripted", "--script", str(script),
             "--python", self.python, "--no-coverage", "--rounds", "0",
             "--out", str(output)],
            cwd=self.root, env=env, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        report = json.loads((output / "report.json").read_text())
        self.assertEqual(report["status"], "failed")
        self.assertIn("complete test report", report["message"])
        self.assertEqual(report["ledger"]["entries"], [])
        self.assertEqual(report["ledger"]["total_tokens"], 0)
        self.assertEqual(report["test_files"], {})
        self.assertIn("No module named pytest", report["final"]["output"])
        self.assertEqual((output / "testpilot.patch").read_bytes(), b"")
        self.assertTrue((output / "report.html").is_file())
        self.assertIn("complete test report", (output / "report.md").read_text())
        self.assertEqual((self.repo / "calc.py").read_text(), SOURCE)


if __name__ == "__main__":
    unittest.main()
