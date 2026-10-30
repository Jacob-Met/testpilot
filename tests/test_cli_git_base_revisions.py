"""Real Git must receive --git-base as a revision, including option-shaped text."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import testpilot

PACKAGE_ROOT = Path(testpilot.__file__).resolve().parent.parent


class GitBaseRevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="testpilot-git-base-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "project"
        self.repo.mkdir()
        self.subject = self.repo / "calc.py"
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        PYTHONPATH=str(PACKAGE_ROOT), PYTHONDONTWRITEBYTECODE="1")
        self.git("init", "-q")
        for value in (1, 2):
            self.subject.write_text(f"def answer():\n    return {value}\n", encoding="utf-8")
            self.git("add", "calc.py")
            self.git("-c", "user.name=TestPilot Fixture", "-c",
                     "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
                     "commit", "-qm", f"fixture {value}")
        self.git("tag", "fixture-base")
        self.git("branch", "fixture-branch")
        self.subject.write_text("def answer():\n    return 3\n", encoding="utf-8")

    def process(self, command, data=None):
        return subprocess.run([str(part) for part in command], cwd=PACKAGE_ROOT,
                              env=self.env, input=data, capture_output=True, timeout=20)

    def git(self, *args):
        result = self.process(["git", "-C", self.repo, *args])
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def project_state(self, *, index_bytes=True):
        state = {name: hashlib.sha256((self.repo / name).read_bytes()).hexdigest()
                 for name in ("calc.py", ".git/config")}
        # A successful native Git diff may refresh cached stat data in the index.
        # Refused revisions must preserve even those bytes; valid reads preserve entries.
        index = ((self.repo / ".git/index").read_bytes() if index_bytes
                 else self.git("ls-files", "--stage", "-z"))
        state["index"] = hashlib.sha256(index).hexdigest()
        return state

    def preview(self, base):
        return self.process([sys.executable, "-B", "-m", "testpilot", "targets",
                             "--repo", self.repo, "--git-base=" + base, "--json"])

    def assert_refused(self, value):
        before = self.project_state()
        result = self.preview(value)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"cannot inspect targets", result.stderr)
        self.assertEqual(self.project_state(), before)

    def assert_option_refused(self, value):
        trace = self.root / "git-option-trace.txt"
        self.env["GIT_TRACE"] = str(trace)
        self.assert_refused(value)
        self.assertFalse(trace.exists(), "Option-shaped input started Git")

    def test_real_revisions_keep_complete_targets(self):
        expected = [{"path": "calc.py", "module": "calc", "qualname": "answer",
                     "lineno": 1, "end_lineno": 2, "changed_lines": [2],
                     "source": "def answer():\n    return 3", "is_method": False}]
        before = self.project_state(index_bytes=False)
        revision = self.git("rev-parse", "HEAD").decode().strip()
        refs = ["HEAD", "HEAD^", "HEAD~1", "fixture-base", "fixture-branch",
                revision, revision[:10], "HEAD~1..HEAD", "HEAD~1...HEAD"]
        for ref in refs:
            with self.subTest(ref=ref):
                result = self.preview(ref)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["changed_functions"], expected)
        self.assertEqual(self.project_state(index_bytes=False), before)

    def test_option_shaped_bases_cannot_change_diff_mode(self):
        for value in ("--stat", "--name-only", "--numstat", "--ext-diff", "--textconv",
                      "--no-index", "--exit-code", "--", "--end-of-options", "-R", "-"):
            with self.subTest(value=value):
                self.assert_option_refused(value)

    def test_output_shaped_bases_preserve_existing_and_missing_files(self):
        for occupied in (True, False):
            with self.subTest(occupied=occupied):
                output = self.root / ("retained review.txt" if occupied else "absent review.txt")
                original = b"Retain this independently saved review.\n"
                if occupied:
                    output.write_bytes(original)
                self.assert_option_refused("--output=" + str(output))
                if occupied:
                    self.assertEqual(output.read_bytes(), original)
                else:
                    self.assertFalse(output.exists())

    def test_run_refusal_keeps_saved_reports_and_named_file(self):
        responses = self.root / "responses"
        responses.mkdir()
        (responses / "01.txt").write_text("No live model is used.\n", encoding="utf-8")
        out = self.root / "review"
        out.mkdir()
        originals = {name: ("Retain " + name + "\n").encode()
                     for name in ("testpilot.patch", "report.json", "report.md", "report.html")}
        for name, body in originals.items():
            (out / name).write_bytes(body)
        named = self.root / "retained diff destination.txt"
        named.write_bytes(b"Retain this file.\n")
        before = self.project_state()
        result = self.process([sys.executable, "-B", "-m", "testpilot", "run",
                               "--repo", self.repo, "--git-base=--output=" + str(named),
                               "--backend", "scripted", "--script", responses, "--out", out])
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(b"wrote ", result.stdout)
        self.assertEqual(named.read_bytes(), b"Retain this file.\n")
        self.assertEqual({name: (out / name).read_bytes() for name in originals}, originals)
        self.assertEqual(self.project_state(), before)

    def test_saved_file_and_stdin_keep_the_git_target_records(self):
        patch = self.git("diff", "HEAD", "--", "*.py")
        saved = self.root / "change.diff"
        saved.write_bytes(patch)
        expected = json.loads(self.preview("HEAD").stdout)
        for source, data in ((str(saved), None), ("-", patch)):
            with self.subTest(source=source):
                result = self.process([sys.executable, "-B", "-m", "testpilot", "targets",
                                       "--repo", self.repo, "--diff", source, "--json"], data)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), expected)
        self.assertEqual(saved.read_bytes(), patch)

    def test_unknown_revisions_and_unchanged_preview_keep_existing_behavior(self):
        for ref in ("missing-testpilot-fixture-ref", "HEAD^{not-a-type}", "HEAD with spaces"):
            with self.subTest(ref=ref):
                self.assert_refused(ref)
        self.subject.write_text("def answer():\n    return 2\n", encoding="utf-8")
        before = self.project_state(index_bytes=False)
        result = self.preview("HEAD")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"changed_functions": []})
        self.assertEqual(self.project_state(index_bytes=False), before)


if __name__ == "__main__":
    unittest.main()
