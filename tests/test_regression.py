"""Real Git/native pytest controls for the paired retained-suite command."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import testpilot

SOURCE = Path(testpilot.__file__).resolve().parents[1]
RETAINED = "from subject import answer\n\ndef test_retained_answer():\n    assert answer() == 7\n"


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="testpilot-regression-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "project with spaces"
        self.repo.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_AUTHOR_NAME="TestPilot synthetic author",
                        GIT_AUTHOR_EMAIL="tests@example.invalid",
                        GIT_COMMITTER_NAME="TestPilot synthetic author",
                        GIT_COMMITTER_EMAIL="tests@example.invalid",
                        PYTHONDONTWRITEBYTECODE="1")
        self.git("init", "--quiet", "--template=", "--initial-branch=main")
        self.write("subject.py", "def answer():\n    return 2\n")
        self.write("tests/test_existing.py", "def test_existing():\n    assert True\n")
        self.before = self.commit("before")
        self.write("subject.py", "def answer():\n    return 7\n")
        self.after = self.commit("after")
        self.report = self.root / "saved.json"
        self.save_report({"tests/test_retained.py": RETAINED})

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], env=self.env,
                              check=True, capture_output=True, text=True).stdout.strip()

    def write(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="")
        return path

    def commit(self, message):
        self.git("add", "--all")
        self.git("-c", "core.hooksPath=" + os.devnull, "commit", "--quiet", "-m", message)
        return self.git("rev-parse", "HEAD")

    def save_report(self, files, **extra):
        self.report.write_text(json.dumps({"status": "verified", "test_files": files, **extra}))

    def module(self):
        return importlib.import_module("testpilot.regression")

    def run_pair(self, **kwargs):
        options = {"before": self.before, "after": self.after,
                   "python": sys.executable, "timeout_s": 10}
        options.update(kwargs)
        return self.module().check_regression(self.repo, self.report, **options)

    def protected(self):
        return {str(p.relative_to(self.repo)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.repo.rglob("*") if p.is_file()}

    def cli(self, *extra, output=None):
        output = output or self.root / "paired"
        env = dict(self.env, PYTHONPATH=str(SOURCE))
        return subprocess.run([sys.executable, "-B", "-m", "testpilot", "regression",
                               "--repo", str(self.repo), "--report", str(self.report),
                               "--before", self.before, "--after", self.after,
                               "--python", sys.executable, "--timeout", "10",
                               "--out", str(output), *extra], env=env,
                              capture_output=True, text=True, timeout=45)

    def test_real_cli_uses_committed_bytes_and_preserves_dirty_worktree(self):
        self.write("subject.py", "raise RuntimeError('dirty source must not run')\n")
        self.write("untracked.txt", "keep exactly\n")
        original = self.protected()
        report_bytes = self.report.read_bytes()
        process = self.cli()
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads((self.root / "paired/regression.json").read_text())
        self.assertEqual(result["schema"], "testpilot.regression/1")
        self.assertEqual(result["status"], "verified_regression")
        self.assertTrue(result["ok"])
        self.assertEqual(result["before"]["commit"], self.before)
        self.assertEqual(result["after"]["commit"], self.after)
        self.assertEqual(result["before"]["tree"], self.git("rev-parse", self.before + "^{tree}"))
        self.assertEqual(result["before"]["result"]["generated"]["failed"], 1)
        self.assertEqual(result["after"]["result"]["generated"]["passed"], 1)
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["test_files"], {"tests/test_retained.py": RETAINED})
        self.assertEqual(len(result["comparison"]["witnesses"]), 1)
        self.assertEqual(result["source_report"]["sha256"], hashlib.sha256(report_bytes).hexdigest())
        self.assertIn("verified_regression", (self.root / "paired/regression.md").read_text())
        self.assertEqual(self.protected(), original)
        self.assertEqual(self.report.read_bytes(), report_bytes)

    def test_same_revision_and_old_recorded_status_do_not_create_proof(self):
        result = self.run_pair(before=self.after)
        self.assertEqual(result["status"], "not_regression")
        self.assertFalse(result["ok"])
        self.assertEqual(result["source_report"]["recorded_status"], "verified")
        self.assertEqual(result["comparison"]["witnesses"], [])
        self.assertTrue(result["before"]["result"]["ok"])

    def test_after_assertion_failure_is_after_failed(self):
        result = self.run_pair(before=self.after, after=self.before)
        self.assertEqual(result["status"], "after_failed")
        self.assertTrue(result["comparison"]["comparable"])
        self.assertEqual(result["comparison"]["witnesses"], [])

    def test_existing_test_failure_cannot_prove_generated_regression(self):
        self.write("tests/test_existing.py", "def test_existing():\n    assert False\n")
        old = self.commit("existing failure; generated already correct")
        self.write("tests/test_existing.py", "def test_existing():\n    assert True\n")
        new = self.commit("existing correction")
        result = self.run_pair(before=old, after=new)
        self.assertEqual(result["before"]["result"]["failed"], 1)
        self.assertEqual(result["before"]["result"]["generated"]["failed"], 0)
        self.assertEqual(result["status"], "not_regression")

    def test_generated_skip_is_inconclusive(self):
        self.save_report({"tests/test_retained.py": "import pytest\n" + RETAINED.replace(
            "def test_retained_answer():", "@pytest.mark.skip(reason='no execution')\ndef test_retained_answer():")})
        result = self.run_pair()
        self.assertEqual(result["status"], "inconclusive")
        self.assertFalse(result["comparison"]["comparable"])
        self.assertEqual(result["after"]["result"]["generated"]["skipped"], 1)

    def test_collection_error_is_inconclusive(self):
        self.save_report({"tests/test_retained.py": "import absent_testpilot_receiving_module\n" + RETAINED})
        result = self.run_pair()
        self.assertEqual(result["status"], "inconclusive")
        self.assertGreater(result["before"]["result"]["errors"], 0)

    def test_each_retained_file_must_collect(self):
        self.save_report({"tests/test_retained.py": RETAINED,
                          "tests/test_no_cases.py": "# This saved file has no runnable tests.\n"})
        result = self.run_pair()
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["comparison"]["reason"], "missing_generated_file_collection")

    def test_native_timeout_remains_inconclusive(self):
        self.save_report({"tests/test_retained.py": "import time\ndef test_slow():\n    time.sleep(4)\n"})
        result = self.run_pair(timeout_s=0.4)
        self.assertEqual(result["status"], "inconclusive")
        self.assertTrue(result["before"]["result"]["timed_out"])
        self.assertTrue(result["after"]["result"]["timed_out"])

    def test_git_archive_attributes_do_not_remove_or_substitute_source(self):
        self.write(".gitattributes", "subject.py export-ignore\nmetadata.txt export-subst\n")
        self.write("metadata.txt", "$Format:%H$\n")
        attributes = self.commit("original blobs retained")
        self.save_report({"tests/test_retained.py": RETAINED +
                          "\ndef test_raw_metadata():\n    from pathlib import Path\n"
                          "    assert Path('metadata.txt').read_text() == '$Format:%H$\\n'\n"})
        result = self.run_pair(before=attributes, after=attributes)
        self.assertEqual(result["status"], "not_regression")
        self.assertEqual(result["after"]["result"]["generated"]["passed"], 2)

    def test_git_replacement_and_caller_routing_do_not_change_requested_source(self):
        self.git("replace", self.before, self.after)
        protected = self.protected()
        with patch.dict(os.environ, {"GIT_DIR": str(self.root / "not-the-repository"),
                                     "GIT_WORK_TREE": str(self.root)}):
            result = self.run_pair()
        self.assertEqual(result["status"], "verified_regression")
        self.assertEqual(self.protected(), protected)

    def test_committed_retained_file_must_match_and_both_preflight_before_pytest(self):
        self.write("tests/test_retained.py", "def test_wrong():\n    assert True\n")
        conflict = self.commit("conflicting retained path")
        module = self.module()
        with patch.object(module, "run_pytest", side_effect=AssertionError("must not execute")) as runner:
            with self.assertRaisesRegex(module.RegressionError, "retained test differs"):
                self.run_pair(after=conflict)
            runner.assert_not_called()
        self.write("tests/test_retained.py", RETAINED)
        exact = self.commit("exact retained bytes")
        result = self.run_pair(after=exact)
        self.assertEqual(result["status"], "verified_regression")

    def test_unsupported_tree_mode_refuses_before_execution(self):
        self.git("update-index", "--add", "--cacheinfo", "160000," + self.before + ",vendor")
        self.git("-c", "core.hooksPath=" + os.devnull, "commit", "--quiet", "-m", "gitlink")
        unsupported = self.git("rev-parse", "HEAD")
        module = self.module()
        with patch.object(module, "run_pytest", side_effect=AssertionError("must not execute")) as runner:
            with self.assertRaisesRegex(module.RegressionError, "unsupported Git entry"):
                self.run_pair(after=unsupported)
            runner.assert_not_called()

    def test_limits_and_invalid_inputs_refuse_before_execution(self):
        module = self.module()
        protected = self.protected()
        with patch.object(module, "run_pytest", side_effect=AssertionError("must not execute")) as runner:
            for value in (0, -1, float("nan"), float("inf"), True):
                with self.assertRaisesRegex(module.RegressionError, "finite positive"):
                    self.run_pair(timeout_s=value)
            with self.assertRaises(module.RegressionError):
                self.run_pair(after="does-not-exist")
            with patch.object(module, "MAX_SOURCE_FILES", 1):
                with self.assertRaisesRegex(module.RegressionError, "source files"):
                    self.run_pair()
            with patch.object(module, "MAX_SOURCE_FILE_BYTES", 1):
                with self.assertRaisesRegex(module.RegressionError, "source file"):
                    self.run_pair()
            self.report.write_text('{"test_files": {}, "test_files": {}}')
            with self.assertRaises(module.RegressionError):
                self.run_pair()
            runner.assert_not_called()
        self.assertEqual(self.protected(), protected)

    def test_cli_refusals_preserve_existing_outputs_and_source(self):
        prior = self.root / "existing"
        prior.mkdir()
        (prior / "regression.json").write_bytes(b"prior evidence\n")
        protected = self.protected()
        result = self.cli(output=prior)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("invalid choice", result.stderr)
        self.assertEqual((prior / "regression.json").read_bytes(), b"prior evidence\n")
        internal = self.repo / "output"
        result = self.cli(output=internal)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(internal.exists())
        result = self.cli("--after", "missing-reference")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.root / "paired").exists())
        self.assertEqual(self.protected(), protected)


if __name__ == "__main__":
    unittest.main()
