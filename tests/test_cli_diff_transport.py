"""Exercise raw diff inputs through the actual CLI and native Python decoder."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
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
from testpilot import __main__ as cli

PACKAGE_ROOT = Path(testpilot.__file__).resolve().parent.parent


class RawDiffTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="testpilot-diff-transport-")
        self.root = Path(self.temp.name)
        self.sequence = 0
        self.env = {
            "PATH": os.defpath,
            "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(PACKAGE_ROOT),
            "PYTHONIOENCODING": "utf-8:strict",
            "TMPDIR": str(self.root),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }

    def tearDown(self):
        self.temp.cleanup()

    def run_process(self, args, *, cwd=PACKAGE_ROOT, data=None):
        return subprocess.run(
            [str(arg) for arg in args], cwd=cwd, env=self.env,
            input=data, capture_output=True, timeout=30,
        )

    def git(self, repo, *args):
        result = self.run_process(["git", "-C", repo, *args])
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def project_bytes(self, repo):
        return {
            p.relative_to(repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(repo.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(repo).parts
        }

    def fixture(self, codec, label, *, name="subject.py", additional=()):
        self.sequence += 1
        root = self.root / str(self.sequence)
        repo = root / "project"
        (repo / "tests").mkdir(parents=True)
        specs = [(name, codec, label), *additional]
        expected = []
        for filename, encoding, literal in specs:
            text = (
                f"# coding: {encoding}\n"
                "def value():\n"
                f"    label = {literal!r}\n"
                "    return label, 1\n"
            )
            (repo / filename).write_bytes(text.encode(encoding))
            expected.append((filename, text.replace("return label, 1", "return label, 2"), literal))
        (repo / "tests/test_existing.py").write_text(
            "import importlib\n\n"
            "def test_existing_contract():\n"
            f"    assert importlib.import_module({Path(name).stem!r}).value()[0] == {label!r}\n",
            encoding="utf-8",
        )
        self.git(repo, "init", "-q")
        self.git(repo, "add", ".")
        self.git(repo, "-c", "user.name=TestPilot Fixture",
                 "-c", "user.email=testpilot-fixture@invalid.local",
                 "-c", "commit.gpgsign=false", "commit", "-qm", "before")
        for (filename, encoding, _), (_, text, _) in zip(specs, expected):
            (repo / filename).write_bytes(text.encode(encoding))
        raw = self.git(repo, "diff", "HEAD", "--", "*.py")
        diff = root / "change.diff"
        diff.write_bytes(raw)
        script = root / "script"
        script.mkdir()
        (script / "01.txt").write_text("Check the changed tuple result.", encoding="utf-8")
        fence = chr(96) * 3
        generated = (
            "import importlib\n\n"
            "def test_generated_tuple():\n"
            f"    assert importlib.import_module({Path(name).stem!r}).value() == ({label!r}, 2)\n"
        )
        (script / "02.txt").write_text(
            fence + "python path=tests/test_generated_tuple.py\n" + generated + fence + "\n",
            encoding="utf-8",
        )
        return {"root": root, "repo": repo, "diff": diff, "raw": raw,
                "script": script, "expected": expected, "generated": generated,
                "before": self.project_bytes(repo)}

    def call_cli(self, fixture, operation, route):
        args = [sys.executable, "-B", "-m", "testpilot", operation, "--repo", fixture["repo"]]
        if route == "git":
            args += ["--git-base", "HEAD"]
        else:
            args += ["--diff", "-" if route == "stdin" else fixture["diff"]]
        out = fixture["root"] / ("output-" + route)
        if operation == "targets":
            args += ["--json"]
        else:
            args += ["--backend", "scripted", "--script", fixture["script"],
                     "--rounds", "0", "--python", sys.executable,
                     "--timeout", "15", "--out", out]
        result = self.run_process(args, data=fixture["raw"] if route == "stdin" else None)
        return result, out

    def assert_preview(self, fixture, route):
        result, _ = self.call_cli(fixture, "targets", route)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b"")
        targets = json.loads(result.stdout)["changed_functions"]
        expected = {name: (source, label) for name, source, label in fixture["expected"]}
        self.assertEqual(set(target["path"] for target in targets), set(expected))
        for target in targets:
            source, _ = expected[target["path"]]
            self.assertEqual(target["qualname"], "value")
            self.assertEqual((target["lineno"], target["end_lineno"]), (2, 4))
            self.assertEqual(target["changed_lines"], [4])
            self.assertEqual(target["source"], source.split("\n", 1)[1].rstrip("\n"))
            self.assertEqual(target["module"], Path(target["path"]).stem)
        self.assertEqual(self.project_bytes(fixture["repo"]), fixture["before"])
        return targets

    def test_legacy_git_and_saved_file_previews_keep_native_source_text(self):
        for codec, label in (("latin-1", "café"), ("cp1252", "€")):
            fixture = self.fixture(codec, label)
            with self.assertRaises(UnicodeDecodeError):
                fixture["raw"].decode("utf-8")
            for route in ("git", "file"):
                with self.subTest(codec=codec, route=route):
                    self.assert_preview(fixture, route)

    def test_binary_stdin_works_with_an_explicit_strict_text_decoder(self):
        fixture = self.fixture("latin-1", "café")
        self.assert_preview(fixture, "stdin")
        result, out = self.call_cli(fixture, "run", "stdin")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((out / "report.json").read_text())["status"], "passed")
        self.assertEqual(self.project_bytes(fixture["repo"]), fixture["before"])

    def test_one_diff_can_contain_multiple_source_encodings_and_a_quoted_path(self):
        fixture = self.fixture(
            "utf-8", "naïve", name="café.py",
            additional=(("latin.py", "latin-1", "café"), ("windows.py", "cp1252", "€")),
        )
        with self.assertRaises(UnicodeDecodeError):
            fixture["raw"].decode("utf-8")
        self.assertIn(b"caf\\303\\251.py", fixture["raw"])
        records = [self.assert_preview(fixture, route) for route in ("git", "file", "stdin")]
        self.assertEqual(records[0], records[1])
        self.assertEqual(records[1], records[2])

    def test_raw_diffs_generate_executed_tests_and_exact_applicable_patches(self):
        for codec, label in (("latin-1", "café"), ("cp1252", "€")):
            for route in ("git", "file", "stdin"):
                with self.subTest(codec=codec, route=route):
                    fixture = self.fixture(codec, label)
                    result, out = self.call_cli(fixture, "run", route)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, b"")
                    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
                    self.assertEqual(report["status"], "passed")
                    self.assertEqual(report["tests_written"], 1)
                    self.assertEqual(report["final"]["passed"], 2)
                    self.assertEqual(report["final"]["generated"],
                                     {"collected": 1, "passed": 1, "failed": 0, "error": 0, "skipped": 0})
                    self.assertEqual([entry["role"] for entry in report["ledger"]["entries"]],
                                     ["planner", "editor"])
                    self.assertEqual(report["test_files"],
                                     {"tests/test_generated_tuple.py": fixture["generated"]})
                    self.assertEqual(self.project_bytes(fixture["repo"]), fixture["before"])
                    receiving = fixture["root"] / "receiving"
                    shutil.copytree(fixture["repo"], receiving)
                    self.git(receiving, "apply", "--check", str(out / "testpilot.patch"))
                    self.git(receiving, "apply", str(out / "testpilot.patch"))
                    self.assertEqual((receiving / "tests/test_generated_tuple.py").read_bytes(),
                                     fixture["generated"].encode("utf-8"))
                    received = self.run_process(
                        [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                        cwd=receiving,
                    )
                    self.assertEqual(received.returncode, 0, received.stdout + received.stderr)
                    self.assertIn(b"2 passed", received.stdout)
                    self.assertEqual(self.project_bytes(fixture["repo"]), fixture["before"])

    def test_utf8_and_ascii_inputs_retain_route_parity(self):
        for codec, label in (("ascii", "plain"), ("utf-8", "café")):
            fixture = self.fixture(codec, label)
            fixture["raw"].decode("utf-8")
            records = [self.assert_preview(fixture, route) for route in ("git", "file", "stdin")]
            self.assertEqual(records[0], records[1])
            self.assertEqual(records[1], records[2])

    def test_saved_diff_universal_newlines_remain_supported(self):
        fixture = self.fixture("utf-8", "café")
        for newline in (b"\r\n", b"\r"):
            with self.subTest(newline=newline):
                fixture["diff"].write_bytes(fixture["raw"].replace(b"\n", newline))
                self.assert_preview(fixture, "file")

    def test_text_only_stdin_callers_remain_supported_without_generation(self):
        fixture = self.fixture("utf-8", "café")
        output, errors = io.StringIO(), io.StringIO()
        with (
            patch.object(sys, "stdin", io.StringIO(fixture["raw"].decode("utf-8"))),
            patch.object(cli, "make_client", side_effect=AssertionError("model must not run")),
            patch.object(cli, "TestPilot", side_effect=AssertionError("tests must not run")),
            patch.object(cli.subprocess, "run", side_effect=AssertionError("git must not run")),
            redirect_stdout(output), redirect_stderr(errors),
        ):
            result = cli.main(["targets", "--repo", str(fixture["repo"]), "--diff", "-", "--json"])
        self.assertEqual(result, 0)
        self.assertEqual(errors.getvalue(), "")
        self.assertEqual(json.loads(output.getvalue())["changed_functions"][0]["path"], "subject.py")
        self.assertEqual(self.project_bytes(fixture["repo"]), fixture["before"])


if __name__ == "__main__":
    unittest.main()
