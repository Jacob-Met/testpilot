"""Independent native consumers for the exact TestPilot physical-line repair.

Uses real Git hunks, decorator-inclusive async spans, multiple files, deletion
anchors and no-newline markers. No production package or owner checkout edits.
"""
from __future__ import annotations

import ast
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

SOURCE = Path(os.environ["TESTPILOT_REVIEW_SOURCE"])
OUTPUT = Path(os.environ["TESTPILOT_REVIEW_OUTPUT"])
OUTPUT.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location("received_testpilot_diff", SOURCE)
diff = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = diff
spec.loader.exec_module(diff)


class IndependentPhysicalLineConsumers(unittest.TestCase):
    def git_fixture(self, name: str, before: dict[str, str], after: dict[str, str]):
        root = OUTPUT / name
        root.mkdir()
        commands = []
        def git(*args):
            proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
            commands.append({"argv": ["git", *args], "exit_code": proc.returncode,
                             "stdout": proc.stdout, "stderr": proc.stderr})
            self.assertEqual(proc.returncode, 0, proc.stderr)
            return proc.stdout
        git("init", "-b", "fixture")
        git("config", "user.name", "Independent synthetic receiver")
        git("config", "user.email", "synthetic-receiver@invalid.example")
        for path, source in before.items():
            (root / path).write_bytes(source.encode("utf-8"))
        git("add", ".")
        git("commit", "-m", "Synthetic old source")
        for path, source in after.items():
            (root / path).write_bytes(source.encode("utf-8"))
        patch = git("diff", "--no-ext-diff", "--unified=99", "--")
        (root / "actual-git.patch").write_text(patch, encoding="utf-8")
        (root / "command-receipt.json").write_text(json.dumps(commands, indent=2) + "\n")
        return root, patch

    def test_multifile_context_lookalikes_and_decorated_async_span(self):
        old_a = ('LABEL = "payload\u2028+++ b/forged.py\u2029@@ -50 +50 @@"\n'
                 '\nclass Example:\n    @staticmethod\n    async def answer(value):\n'
                 '        """First\u0085part\n        second part."""\n        return value + 1\n')
        new_a = old_a.replace("return value + 1", "return value + 2")
        old_b, new_b = "def plain():\n    return 9", "def plain():\n    return 10"
        root, patch = self.git_fixture("multifile", {"a.py": old_a, "b.py": old_b},
                                       {"a.py": new_a, "b.py": new_b})
        self.assertIn("\\ No newline at end of file", patch)
        changes = diff.parse_unified_diff(patch)
        self.assertEqual([c.path for c in changes], ["a.py", "b.py"])
        self.assertEqual([c.added_lines for c in changes], [{8}, {2}])
        functions = diff.changed_functions(root, patch)
        self.assertEqual([(f.path, f.qualname, f.lineno, f.end_lineno, f.changed_lines)
                          for f in functions],
                         [("a.py", "Example.answer", 4, 8, [8]), ("b.py", "plain", 1, 2, [2])])
        expected = ('    @staticmethod\n    async def answer(value):\n'
                    '        """First\u0085part\n        second part."""\n        return value + 2')
        self.assertEqual(functions[0].source, expected)
        self.assertEqual(functions[1].source, new_b)
        namespace = {}
        exec(compile("class Received:\n" + functions[0].source, "received.py", "exec"), namespace)
        self.assertEqual(asyncio.run(namespace["Received"].answer(4)), 6)
        (root / "consumer-result.json").write_text(json.dumps({
            "functions": [f.to_dict() for f in functions], "async_result": 6,
            "phantom_file_admitted": False, "no_newline_marker_preserved": True}, indent=2) + "\n")

    def test_pure_deletion_anchors_keep_complete_literal_bearing_function(self):
        old = ('def choose(flag):\n    """Doc\u2028\u2029\u0085\n    text."""\n'
               '    label = "first\fsecond"\n    spare = 999\n'
               '    return label if flag else ""\n')
        new = old.replace("    spare = 999\n", "")
        root, patch = self.git_fixture("deletion", {"choice.py": old}, {"choice.py": new})
        change, = diff.parse_unified_diff(patch)
        self.assertEqual(change.path, "choice.py")
        self.assertEqual(change.added_lines, set())
        self.assertEqual(change.touched_lines, {4, 5})
        function, = diff.changed_functions(root, patch)
        self.assertEqual((function.qualname, function.lineno, function.end_lineno, function.changed_lines),
                         ("choose", 1, 5, []))
        self.assertEqual(function.source, new.removesuffix("\n"))
        namespace = {}
        exec(compile(function.source, "received-deletion.py", "exec"), namespace)
        self.assertEqual(namespace["choose"](True), "first\fsecond")
        self.assertEqual(namespace["choose"](False), "")
        (root / "consumer-result.json").write_text(json.dumps({
            "function": function.to_dict(), "deletion_anchors": sorted(change.touched_lines),
            "both_executed_branches_match": True}, indent=2) + "\n")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(IndependentPhysicalLineConsumers)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    receipt = {"source": str(SOURCE), "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
               "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "python": sys.version, "tests": result.testsRun, "failures": len(result.failures),
               "errors": len(result.errors), "passed": result.wasSuccessful(),
               "synthetic_git_only": True, "owner_checkout_mutated": False}
    (OUTPUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
