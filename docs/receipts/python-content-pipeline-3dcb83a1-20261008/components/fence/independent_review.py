"""Independent fence boundary receiving; replay with SOURCE_DIR RECEIPT_JSON."""
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
from testpilot.loop import TestPilot, parse_test_files
from testpilot.model import RoutingConfig, ScriptedModel

FENCE = chr(96) * 3
FIRST = ('from sample import double\n\n'
         'def test_inline_fence():\n'
         '    text = "inline' + FENCE + 'python marker' + FENCE + 'tail"\n'
         '    assert double(text.count(chr(96))) == 12\n').replace("\n", "\r\n")
SECOND = ("from sample import double\n\n"
          "def test_second_block():\n    assert double(3) == 6\n")
REPLY = (FENCE + "python path=tests/test_fence_a.py\r\n" + FIRST
         + " \t" + FENCE + chr(96) + " \t\r\n"
         + "Authored text between blocks.\n"
         + FENCE + "python path=tests/test_fence_b.py\n" + SECOND
         + FENCE + "\n")
observations = {}


class FenceReceiving(unittest.TestCase):
    def test_two_blocks_preserve_inline_ticks_crlf_and_longer_closer(self):
        files, warnings = parse_test_files(REPLY)
        expected = {"tests/test_fence_a.py": FIRST, "tests/test_fence_b.py": SECOND}
        observations["parser"] = {"files": files, "warnings": warnings,
                                  "exact_files": files == expected}
        self.assertEqual(files, expected)
        self.assertEqual(warnings, [])
        for name, source in files.items():
            compile(source, name, "exec")

    def test_real_testpilot_receives_both_files_and_valid_patch(self):
        with tempfile.TemporaryDirectory(prefix="testpilot-fence-receiver-") as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            source = repo / "sample.py"
            source.write_text("def double(value):\n    return value\n")
            (repo / "tests").mkdir()
            existing = repo / "tests/test_existing.py"
            sentinel = "from sample import double\n\ndef test_zero():\n    assert double(0) == 0\n"
            existing.write_text(sentinel)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
            current = "def double(value):\n    return value * 2\n"
            source.write_text(current)
            diff = subprocess.run(["git", "diff", "--", "sample.py"], cwd=repo,
                                  check=True, capture_output=True, text=True).stdout
            client = ScriptedModel(["Exercise inline delimiter data and the second block.", REPLY])
            result = TestPilot(client, RoutingConfig("review-plan", "review-edit"),
                               coverage=False, timeout_s=30, max_repair_rounds=0,
                               python=sys.executable).run(repo, diff)
            patch = root / "generated.patch"
            patch.write_text(result.patch, encoding="utf-8")
            apply = subprocess.run(["git", "-C", str(repo), "apply", "--check", str(patch)],
                                   capture_output=True, text=True)
            unchanged = source.read_text() == current and existing.read_text() == sentinel
            observations["consumer"] = {
                "status": result.status, "tests_written": result.tests_written, "final": result.final,
                "files": result.test_files, "model_calls": len(client.calls),
                "git_apply_check": apply.returncode, "git_apply_stderr": apply.stderr,
                "originals_unchanged": unchanged}
            self.assertEqual(result.status, "passed")
            self.assertEqual(result.tests_written, 2)
            self.assertEqual(result.final["passed"], 3)
            self.assertEqual(result.test_files,
                             {"tests/test_fence_a.py": FIRST, "tests/test_fence_b.py": SECOND})
            self.assertEqual(len(client.calls), 2)
            self.assertEqual(apply.returncode, 0, apply.stderr)
            self.assertTrue(unchanged)


def pin(path):
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}


result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(FenceReceiving))
receipt = {"source": str(SOURCE), "python": sys.version, "harness": pin(Path(__file__)),
           "package": {path.name: pin(path) for path in sorted((SOURCE / "testpilot").glob("*.py"))},
           "tests_run": result.testsRun, "failures": len(result.failures),
           "errors": len(result.errors), "skips": len(result.skipped),
           "successful": result.wasSuccessful(), "observations": observations}
RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"tests_run": result.testsRun, "failures": len(result.failures),
                  "errors": len(result.errors), "successful": result.wasSuccessful()}))
raise SystemExit(0 if result.wasSuccessful() else 1)
