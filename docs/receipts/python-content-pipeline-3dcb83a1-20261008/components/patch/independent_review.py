"""Independent TestPilot patch receiver; authored fixtures only.

Replay: python3 independent_review.py SOURCE_DIRECTORY RECEIPT_JSON
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(sys.argv[1]).resolve()
RECEIPT = Path(sys.argv[2]).resolve()
sys.dont_write_bytecode = True
sys.path.insert(0, str(SOURCE))
from testpilot.loop import TestPilot
from testpilot.model import RoutingConfig, ScriptedModel

observation = {}


class EmittedPatchReceiving(unittest.TestCase):
    def test_real_generated_literal_patch_applies_exactly_and_passes_pytest(self):
        with tempfile.TemporaryDirectory(prefix="testpilot-patch-receiver-") as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            source = repo / "sample.py"
            source.write_text("def double(value):\n    return value\n", encoding="utf-8")
            tests = repo / "tests"
            tests.mkdir()
            existing = tests / "test_literals.py"
            sentinel = ("from sample import double\n\n"
                        "def test_existing_zero():\n    assert double(0) == 0\n")
            existing.write_text(sentinel, encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
            changed = "def double(value):\n    return value * 2\n"
            source.write_text(changed, encoding="utf-8")
            diff = subprocess.run(["git", "diff", "--", "sample.py"], cwd=repo,
                                  check=True, capture_output=True, text=True).stdout

            # Eight characters split by str.splitlines but not by Git's LF lines.
            label = "a" + "".join(chr(n) for n in
                                  (11, 12, 28, 29, 30, 133, 0x2028, 0x2029)) + "b"
            generated = (
                "from sample import double\n\n"
                f'LABEL = "{label}"\n\n'
                "def test_literal_length():\n    assert double(len(LABEL)) == 20\n\n"
                "def test_literal_identity():\n    assert double(ord(LABEL[-1])) == 196\n")
            compile(generated, "authored-generated.py", "exec")
            fence = chr(96) * 3
            client = ScriptedModel([
                "Check length and final-character behavior using the authored literal.",
                fence + "python path=tests/test_literals.py\n" + generated + fence])
            result = TestPilot(client, RoutingConfig("review-plan", "review-edit"),
                               coverage=False, timeout_s=30, max_repair_rounds=0,
                               python=sys.executable).run(repo, diff)
            aliases = sorted(result.test_files)
            expected_alias = "tests/test_literals_testpilot.py"
            patch_path = root / "generated.patch"
            patch_path.write_text(result.patch, encoding="utf-8")
            before_apply_unchanged = (
                source.read_bytes() == changed.encode("utf-8")
                and existing.read_bytes() == sentinel.encode("utf-8")
                and not (repo / expected_alias).exists())
            check = subprocess.run(
                ["git", "-C", str(repo), "apply", "--check", str(patch_path)],
                capture_output=True, text=True)
            applied = None
            applied_exact = False
            receiving_run = None
            if check.returncode == 0:
                applied = subprocess.run(
                    ["git", "-C", str(repo), "apply", str(patch_path)],
                    capture_output=True, text=True)
                if applied.returncode == 0:
                    applied_exact = ((repo / expected_alias).read_bytes()
                                     == result.test_files[expected_alias].encode("utf-8"))
                    receiving_run = subprocess.run(
                        [sys.executable, "-m", "pytest", "-q"], cwd=repo,
                        capture_output=True, text=True, timeout=30)
            after_apply_originals_unchanged = (
                source.read_bytes() == changed.encode("utf-8")
                and existing.read_bytes() == sentinel.encode("utf-8"))
            observation.update({
                "status": result.status, "tests_written": result.tests_written,
                "final": result.final, "model_calls": len(client.calls),
                "generated_aliases": aliases, "literal_codepoints": [ord(c) for c in label],
                "generated": generated, "patch": result.patch,
                "before_apply_unchanged": before_apply_unchanged,
                "git_apply_check": check.returncode, "git_apply_stderr": check.stderr,
                "git_apply": applied.returncode if applied else None,
                "applied_exact_bytes": applied_exact,
                "receiving_pytest": {"returncode": receiving_run.returncode,
                                    "stdout": receiving_run.stdout,
                                    "stderr": receiving_run.stderr} if receiving_run else None,
                "after_apply_originals_unchanged": after_apply_originals_unchanged})
            self.assertEqual(result.status, "passed")
            self.assertEqual(result.tests_written, 2)
            self.assertEqual(result.final["passed"], 3)
            self.assertEqual(len(client.calls), 2)
            self.assertEqual(aliases, [expected_alias])
            self.assertTrue(before_apply_unchanged)
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertTrue(applied_exact)
            self.assertTrue(after_apply_originals_unchanged)
            self.assertEqual(receiving_run.returncode, 0, receiving_run.stdout)
            self.assertIn("3 passed", receiving_run.stdout)


def pin(path):
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}


result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(EmittedPatchReceiving))
receipt = {"source": str(SOURCE), "python": sys.version, "harness": pin(Path(__file__)),
           "package": {path.name: pin(path) for path in sorted((SOURCE / "testpilot").glob("*.py"))},
           "tests_run": result.testsRun, "failures": len(result.failures),
           "errors": len(result.errors), "skips": len(result.skipped),
           "successful": result.wasSuccessful(), "observation": observation}
RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"receipt": str(RECEIPT), "tests_run": result.testsRun,
                  "failures": len(result.failures), "errors": len(result.errors),
                  "successful": result.wasSuccessful()}))
raise SystemExit(0 if result.wasSuccessful() else 1)
