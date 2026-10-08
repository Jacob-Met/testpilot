"""Independent real Git/pytest receiving for the paired retained-suite command."""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import testpilot
from testpilot.recheck import read_saved_tests

SOURCE = Path(testpilot.__file__).resolve().parent.parent
FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "regression_receiving.json").read_text())


class PairedRevisionReceiving(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="testpilot-paired-peer-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.python = os.environ.get("TESTPILOT_RECEIVING_PYTHON", sys.executable)
        self.env = dict(os.environ)
        self.env.update(
            PYTHONDONTWRITEBYTECODE="1", GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL=os.devnull, GIT_AUTHOR_NAME="Native receiver",
            GIT_AUTHOR_EMAIL="receiver@example.invalid", GIT_COMMITTER_NAME="Native receiver",
            GIT_COMMITTER_EMAIL="receiver@example.invalid",
            GIT_AUTHOR_DATE="2026-10-08T12:00:00Z", GIT_COMMITTER_DATE="2026-10-08T12:00:00Z",
        )
        for name in list(self.env):
            if name.startswith("GIT_") and name not in {
                "GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL", "GIT_AUTHOR_NAME",
                "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL",
                "GIT_AUTHOR_DATE", "GIT_COMMITTER_DATE",
            }:
                self.env.pop(name)

    def git(self, repo, *args):
        run = subprocess.run(
            ["git", "-C", str(repo), *args], env=self.env, capture_output=True, check=False,
        )
        self.assertEqual(run.returncode, 0, run.stderr.decode())
        return run.stdout

    def repository(self):
        repo = self.home / "source"
        repo.mkdir()
        self.git(repo, "init", "-q", "--initial-branch=main")
        self.git(repo, "config", "core.autocrlf", "false")
        return repo

    def commit(self, repo, files, ref):
        for name, content in files.items():
            path = repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode())
            if name == "tool.py":
                path.chmod(0o755)
        self.git(repo, "add", "--all")
        tree = self.git(repo, "write-tree").decode().strip()
        # Deliberately no -p: the public comparison must admit non-ancestor refs.
        commit = self.git(repo, "commit-tree", tree, "-m", ref).decode().strip()
        self.git(repo, "update-ref", "refs/heads/" + ref, commit)
        return commit, tree

    def report(self, retained):
        path = self.home / "saved-report.json"
        data = {**FIXTURE["report_context"], "test_files": retained}
        path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode())
        return path

    def inventory(self, repo):
        return {
            path.relative_to(repo).as_posix(): (stat.S_IMODE(path.stat().st_mode), hashlib.sha256(path.read_bytes()).hexdigest())
            for path in repo.rglob("*") if path.is_file()
        }

    def signature(self, repo, commit):
        entries = []
        for row in self.git(repo, "ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
            if not row:
                continue
            metadata, path = row.split(b"\t", 1)
            mode, kind, blob = metadata.split()
            self.assertEqual(kind, b"blob")
            contents = self.git(repo, "cat-file", "blob", blob.decode())
            entries.append({"path": path.decode(), "mode": mode.decode(), "blob": blob.decode(), "bytes": len(contents)})
        entries.sort(key=lambda item: item["path"].encode())
        encoded = json.dumps(entries, ensure_ascii=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest(), len(entries), sum(item["bytes"] for item in entries)

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec("testpilot.regression"), "original source has no paired regression capability")
        return importlib.import_module("testpilot.regression")

    def cli(self, repo, report, before, after, out):
        env = {**self.env, "PYTHONPATH": str(SOURCE)}
        return subprocess.run(
            [self.python, "-B", "-m", "testpilot", "regression", "--repo", str(repo),
             "--report", str(report), "--before", before, "--after", after,
             "--out", str(out), "--python", self.python, "--timeout", "20"],
            cwd=self.home, env=env, capture_output=True, check=False, timeout=55,
        )

    def save_evidence(self, name, result):
        destination = os.environ.get("TESTPILOT_RECEIVING_EVIDENCE")
        if destination:
            path = Path(destination)
            path.mkdir(parents=True, exist_ok=True)
            (path / (name + ".json")).write_text(json.dumps(result, indent=2) + "\n")

    def bucket_pair(self):
        repo = self.repository()
        assets = FIXTURE["assets"]
        before = self.commit(repo, {**assets, "buckets.py": FIXTURE["modules"]["before"]}, "main")
        after = self.commit(repo, {"buckets.py": FIXTURE["modules"]["after"]}, "after")
        report = self.report({"tests/test_generated.py": FIXTURE["retained"]["regression"]})
        return repo, before, after, report

    def test_original_saved_report_control(self):
        report = self.report({"tests/test_z.py": "def test_z():\n    assert True\n",
                              "tests/test_a.py": FIXTURE["retained"]["unchanged"]})
        saved = read_saved_tests(report)
        self.assertEqual([name for name, _ in saved.tests], ["tests/test_a.py", "tests/test_z.py"])
        self.assertEqual(saved.sha256, hashlib.sha256(report.read_bytes()).hexdigest())
        self.assertEqual(saved.source_status, "recorded-generation-failed")

    def test_actual_cli_uses_raw_nonancestor_commits_and_preserves_inputs(self):
        repo, before, after, report = self.bucket_pair()
        (repo / "buckets.py").write_text("raise RuntimeError('dirty checkout must not run')\n")
        (repo / "untracked-note.txt").write_text("Keep my unfinished note.\n")
        snapshot, original = self.inventory(repo), report.read_bytes()
        out = self.home / "paired-output"
        run = self.cli(repo, report, "main", "after", out)
        self.assertEqual(run.returncode, 0, run.stderr.decode())
        result = json.loads((out / "regression.json").read_bytes())
        self.save_evidence("committed-cli-witness", result)
        self.assertEqual(result["schema"], "testpilot.regression/1")
        self.assertEqual(result["status"], "verified_regression")
        self.assertIs(result["ok"], True)
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["test_files"], json.loads(original)["test_files"])
        self.assertEqual(result["source_report"]["sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(result["source_report"]["recorded_status"], "recorded-generation-failed")
        self.assertIs(result["comparison"]["comparable"], True)
        witnesses = result["comparison"]["witnesses"]
        self.assertEqual(len(witnesses), 2)
        self.assertEqual({item["nodeid"].split("[")[-1] for item in witnesses}, {"negative-edge]", "negative-next]"})
        self.assertTrue(all(item["generated_file"] == "tests/test_generated.py" and item["before"] == "failed" and item["after"] == "passed" for item in witnesses))
        self.assertEqual(len(result["comparison"]["case_pairs"]), 4)
        for phase, requested, expected in [("before", "main", before), ("after", "after", after)]:
            received = result[phase]
            signature, count, size = self.signature(repo, expected[0])
            self.assertEqual((received["commit"], received["tree"]), expected)
            self.assertEqual(received["requested_ref"], requested)
            self.assertEqual((received["snapshot_sha256"], received["source_files"], received["source_bytes"]), (signature, count, size))
            self.assertIs(received["result"]["junit_available"], True)
            self.assertEqual(received["result"]["generated"]["collected"], 4)
        self.assertIn("verified_regression", (out / "regression.md").read_text())
        self.assertEqual(report.read_bytes(), original)
        self.assertEqual(self.inventory(repo), snapshot)

    def test_existing_suite_failure_never_becomes_a_generated_witness(self):
        module = self.module()
        repo = self.repository()
        self.commit(repo, {"fixed.py": FIXTURE["modules"]["unchanged"], "tests/test_existing.py": FIXTURE["existing"]["fail"]}, "main")
        self.commit(repo, {"tests/test_existing.py": FIXTURE["existing"]["pass"]}, "after")
        report = self.report({"tests/test_generated.py": FIXTURE["retained"]["unchanged"]})
        snapshot, original = self.inventory(repo), report.read_bytes()
        result = module.check_regression(repo, report, before="main", after="after", timeout_s=20, python=self.python)
        self.save_evidence("existing-failure-not-witness", result)
        self.assertEqual(result["status"], "not_regression")
        self.assertIs(result["ok"], False)
        self.assertIs(result["comparison"]["comparable"], True)
        self.assertEqual(result["comparison"]["witnesses"], [])
        self.assertEqual(result["before"]["result"]["failed"], 1)
        self.assertEqual([(item["before"], item["after"]) for item in result["comparison"]["case_pairs"]], [("passed", "passed")])
        self.assertEqual((self.inventory(repo), report.read_bytes()), (snapshot, original))

    def test_real_parametrized_identity_drift_is_inconclusive(self):
        module = self.module()
        repo = self.repository()
        self.commit(repo, {"identities.py": FIXTURE["modules"]["drift_before"]}, "main")
        self.commit(repo, {"identities.py": FIXTURE["modules"]["drift_after"]}, "after")
        report = self.report({"tests/test_generated.py": FIXTURE["retained"]["drift"]})
        snapshot = self.inventory(repo)
        result = module.check_regression(repo, report, before="main", after="after", timeout_s=20, python=self.python)
        self.save_evidence("generated-identity-drift", result)
        self.assertEqual(result["status"], "inconclusive")
        self.assertIs(result["comparison"]["comparable"], False)
        self.assertEqual(result["comparison"]["witnesses"], [])
        self.assertIn("before-only", json.dumps(result["comparison"]["unmatched_before"]))
        self.assertIn("after-only", json.dumps(result["comparison"]["unmatched_after"]))
        self.assertEqual(self.inventory(repo), snapshot)

    def test_actual_reverse_cli_reports_after_failure(self):
        repo, _, _, report = self.bucket_pair()
        snapshot, original = self.inventory(repo), report.read_bytes()
        out = self.home / "reversed-output"
        run = self.cli(repo, report, "after", "main", out)
        self.assertEqual(run.returncode, 1, run.stderr.decode())
        result = json.loads((out / "regression.json").read_bytes())
        self.save_evidence("reverse-after-failed", result)
        self.assertEqual(result["status"], "after_failed")
        self.assertIs(result["ok"], False)
        self.assertIs(result["comparison"]["comparable"], True)
        self.assertEqual(result["comparison"]["witnesses"], [])
        self.assertEqual(result["after"]["result"]["generated"]["failed"], 2)
        self.assertEqual((self.inventory(repo), report.read_bytes()), (snapshot, original))

    def test_both_trees_are_admitted_before_execution_and_output_is_preserved(self):
        module = self.module()
        repo = self.repository()
        marker = self.home / "collection-must-not-start"
        conftest = f"from pathlib import Path\nPath({str(marker)!r}).write_text('pytest started')\n"
        self.commit(repo, {"conftest.py": conftest}, "main")
        self.commit(repo, {"tests/test_generated.py": "def test_conflicting():\n    assert False\n"}, "after")
        report = self.report({"tests/test_generated.py": FIXTURE["retained"]["placement"]})
        snapshot, original = self.inventory(repo), report.read_bytes()
        with self.assertRaises(module.RegressionError):
            module.check_regression(repo, report, before="main", after="after", timeout_s=20, python=self.python)
        self.assertFalse(marker.exists())
        existing = self.home / "existing-output"
        existing.mkdir()
        (existing / "keep.txt").write_text("original output")
        run = self.cli(repo, report, "main", "after", existing)
        self.assertEqual(run.returncode, 2, run.stderr.decode())
        self.assertEqual(sorted(path.name for path in existing.iterdir()), ["keep.txt"])
        self.assertEqual((existing / "keep.txt").read_text(), "original output")
        internal = repo / "forbidden-output"
        refused = self.cli(repo, report, "main", "after", internal)
        self.assertEqual(refused.returncode, 2, refused.stderr.decode())
        self.assertFalse(internal.exists())
        self.assertFalse(marker.exists())
        self.assertEqual((self.inventory(repo), report.read_bytes()), (snapshot, original))


if __name__ == "__main__":
    unittest.main(verbosity=2)
