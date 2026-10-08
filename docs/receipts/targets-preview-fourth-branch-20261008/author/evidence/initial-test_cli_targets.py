"""Native CLI receiving for target previews; no model or pytest dependency."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import testpilot
from testpilot import __main__ as cli

PACKAGE_ROOT = Path(testpilot.__file__).resolve().parent.parent
CLI_RECEIPTS = []


class TargetPreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="testpilot-target-preview-")
        self.root = Path(self.temp.name)
        self.repo = self.root / "project"
        (self.repo / "src").mkdir(parents=True)
        (self.repo / "tests").mkdir()
        self.subject = self.repo / "src" / "caf\u00e9.py"
        self.original = (
            "from pathlib import Path\n"
            'Path(__file__).with_name("source-imported").write_text("unexpected")\n'
            'raise RuntimeError("project source must not be imported")\n\n'
            "def unchanged(value):\n    return value\n\n"
            "class Arithmetic:\n"
            "    @staticmethod\n"
            "    def scale(value):\n        return value * 2\n"
        )
        self.subject.write_text(self.original, encoding="utf-8")
        (self.repo / "conftest.py").write_text(
            "from pathlib import Path\n"
            'Path(__file__).with_name("pytest-started").write_text("unexpected")\n'
            'raise RuntimeError("project pytest must not run")\n',
            encoding="utf-8",
        )
        self.env = {
            "PATH": os.defpath,
            "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(self.root),
            "TESTPILOT_BACKEND": "preview-must-not-construct-a-backend",
        }
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "user.name=TestPilot Fixture",
                 "-c", "user.email=testpilot-fixture@invalid.local",
                 "-c", "commit.gpgsign=false", "commit", "-q", "-m", "before")
        self.subject.write_text(self.original.replace("value * 2", "value * 3"), encoding="utf-8")
        self.diff_text = self.git("diff", "HEAD", "--", "*.py")
        self.diff = self.root / "change.diff"
        self.diff.write_text(self.diff_text, encoding="utf-8")
        self.before = self.project_bytes()

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.repo), *args], check=True,
            capture_output=True, text=True, timeout=15, env=self.env,
        ).stdout

    def project_bytes(self):
        return {
            str(path.relative_to(self.repo)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.repo.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(self.repo).parts
        }

    def run_cli(self, *args, stdin=None):
        argv = [sys.executable, "-B", "-m", "testpilot", *map(str, args)]
        result = subprocess.run(
            argv, cwd=PACKAGE_ROOT, env=self.env, input=stdin,
            capture_output=True, text=True, timeout=15,
        )
        CLI_RECEIPTS.append({
            "test": self.id(), "argv": argv, "returncode": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr,
        })
        return result

    def preview(self, *args, stdin=None):
        return self.run_cli("targets", "--repo", self.repo, *args, stdin=stdin)

    def test_git_preview_selects_native_target_without_executing_project(self):
        result = self.preview("--git-base", "HEAD", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        data = json.loads(result.stdout)
        self.assertEqual(set(data), {"changed_functions"})
        self.assertEqual(len(data["changed_functions"]), 1)
        target = data["changed_functions"][0]
        self.assertEqual(target["path"], "src/caf\u00e9.py")
        self.assertEqual(target["module"], "caf\u00e9")
        self.assertEqual(target["qualname"], "Arithmetic.scale")
        self.assertEqual((target["lineno"], target["end_lineno"]), (9, 11))
        self.assertEqual(target["changed_lines"], [11])
        self.assertTrue(target["is_method"])
        self.assertEqual(target["source"],
                         "    @staticmethod\n    def scale(value):\n        return value * 3")
        self.assertEqual(self.project_bytes(), self.before)

    def test_file_and_stdin_preview_have_identical_target_records(self):
        saved = self.preview("--diff", self.diff, "--json")
        piped = self.preview("--diff", "-", "--json", stdin=self.diff_text)
        self.assertEqual(saved.returncode, 0, saved.stderr)
        self.assertEqual(piped.returncode, 0, piped.stderr)
        self.assertEqual(saved.stdout, piped.stdout)
        self.assertEqual(saved.stderr + piped.stderr, "")
        self.assertEqual(self.project_bytes(), self.before)

    def test_default_human_preview_names_the_exact_location(self):
        result = self.preview("--diff", self.diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            '1 changed Python function outside tests\n'
            '"src/caf\\u00e9.py":9-11  "Arithmetic.scale"\n',
        )
        self.assertNotIn("return value", result.stdout)
        self.assertEqual(self.project_bytes(), self.before)

    def test_empty_diff_is_a_successful_empty_preview(self):
        result = self.preview("--diff", "-", "--json", stdin="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"changed_functions": []})
        human = self.preview("--diff", "-", stdin="")
        self.assertEqual(human.returncode, 0, human.stderr)
        self.assertEqual(human.stdout, "0 changed Python functions outside tests\n")
        self.assertEqual(self.project_bytes(), self.before)

    def test_input_and_native_selector_failures_have_no_success_output(self):
        outside = self.root / "outside.py"
        outside.write_text("def outside():\n    return 7\n", encoding="utf-8")
        invalid = (
            "--- a/../outside.py\n+++ b/../outside.py\n"
            "@@ -1,2 +1,2 @@\n def outside():\n-    return 6\n+    return 7\n"
        )
        cases = [
            (("--diff", self.root / "missing.diff"), None),
            (("--git-base", "missing-ref"), None),
            (("--diff", "-"), invalid),
        ]
        for args, stdin in cases:
            with self.subTest(args=args):
                result = self.preview(*args, "--json", stdin=stdin)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn("testpilot: cannot inspect targets:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
        self.subject.write_text("def broken(:\n", encoding="utf-8")
        result = self.preview("--diff", self.diff, "--json")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("testpilot: cannot inspect targets:", result.stderr)
        self.assertEqual(outside.read_text(encoding="utf-8"), "def outside():\n    return 7\n")
        self.assertFalse((self.repo / "src/source-imported").exists())
        self.assertFalse((self.repo / "pytest-started").exists())

    def test_saved_diff_preview_never_constructs_model_or_test_runner(self):
        output, errors = io.StringIO(), io.StringIO()
        tripwire = AssertionError("preview entered generation, subprocess, or pytest")
        with (
            patch.object(cli, "make_client", side_effect=tripwire),
            patch.object(cli, "TestPilot", side_effect=tripwire),
            patch.object(cli, "write_outputs", side_effect=tripwire),
            patch.object(cli.RoutingConfig, "from_env", side_effect=tripwire),
            patch.object(cli.subprocess, "run", side_effect=tripwire),
            patch("testpilot.sandbox.run_pytest", side_effect=tripwire),
            redirect_stdout(output), redirect_stderr(errors),
        ):
            result = cli.main(["targets", "--repo", str(self.repo),
                               "--diff", str(self.diff), "--json"])
        self.assertEqual(result, 0)
        self.assertEqual(errors.getvalue(), "")
        self.assertEqual(len(json.loads(output.getvalue())["changed_functions"]), 1)
        self.assertEqual(self.project_bytes(), self.before)

    def test_help_and_source_options_do_not_accept_generation_options(self):
        help_result = self.run_cli("targets", "--help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("--git-base", help_result.stdout)
        self.assertIn("--json", help_result.stdout)
        for args in (
            (),
            ("--diff", self.diff, "--git-base", "HEAD"),
            ("--diff", self.diff, "--script", self.root),
        ):
            with self.subTest(args=args):
                result = self.preview(*args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
        self.assertEqual(self.project_bytes(), self.before)

    def test_existing_run_retains_native_no_changes_reports(self):
        script = self.root / "script"
        script.mkdir()
        (script / "01.md").write_text("Unused response; no target exists.", encoding="utf-8")
        empty = self.root / "empty.diff"
        empty.write_text("", encoding="utf-8")
        out = self.root / "run-output"
        result = self.run_cli(
            "run", "--repo", self.repo, "--diff", empty,
            "--backend", "scripted", "--script", script,
            "--python", sys.executable, "--rounds", "2", "--out", out,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stderr, "")
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "no_changes")
        self.assertEqual(report["changed_functions"], [])
        self.assertEqual(report["max_repair_rounds"], 2)
        self.assertEqual(report["ledger"]["total_tokens"], 0)
        self.assertEqual(report["ledger"]["by_model"], {})
        self.assertEqual((out / "testpilot.patch").read_bytes(), b"")
        self.assertIn("no_changes", (out / "report.md").read_text(encoding="utf-8"))
        self.assertEqual(self.project_bytes(), self.before)


if __name__ == "__main__":
    unittest.main()
