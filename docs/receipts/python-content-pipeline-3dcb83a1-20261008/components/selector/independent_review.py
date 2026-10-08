"""Independent physical-line receiving with native AST, Git and TestPilot.

Replay: python3 independent_review.py SOURCE_DIRECTORY RECEIPT_JSON
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

SOURCE = Path(sys.argv[1]).resolve()
RECEIPT = Path(sys.argv[2]).resolve()
sys.dont_write_bytecode = True
sys.path.insert(0, str(SOURCE))
from testpilot.diff import changed_functions, functions_touching, parse_unified_diff
from testpilot.loop import TestPilot
from testpilot.model import RoutingConfig, ScriptedModel

SEPARATORS = ("\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029")
observations = {}


def git(repo, *args):
    result = subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-c", "core.hooksPath=/dev/null",
         "-C", str(repo), *args], check=True, capture_output=True)
    return result.stdout.decode("utf-8")


def modified_repo(repo, before, after, existing=None):
    repo.mkdir()
    source = repo / "sample.py"
    source.write_bytes(before.encode("utf-8"))
    if existing is not None:
        (repo / "tests").mkdir()
        (repo / "tests/test_existing.py").write_text(existing, encoding="utf-8")
    git(repo, "init", "-q")
    git(repo, "add", ".")
    source.write_bytes(after.encode("utf-8"))
    return git(repo, "diff", "--unified=0", "--", "sample.py")


class PhysicalLineReceiving(unittest.TestCase):
    def test_crlf_source_keeps_eight_nonphysical_separators(self):
        entries = []
        observations["crlf_source"] = entries
        for separator in SEPARATORS:
            with self.subTest(separator=ascii(separator)):
                source = f'def message():\r\n    return "a{separator}b"\r\n'
                selected = functions_touching(source, "sample.py", {2}, {2})
                expected = f'def message():\n    return "a{separator}b"'
                entries.append({
                    "separator": ascii(separator), "count": len(selected),
                    "source": selected[0].source if selected else None,
                    "exact_source": len(selected) == 1 and selected[0].source == expected})
                self.assertEqual(len(selected), 1)
                item = selected[0]
                self.assertEqual((item.qualname, item.lineno, item.end_lineno, item.changed_lines),
                                 ("message", 1, 2, [2]))
                self.assertEqual(item.source, expected)
                namespace = {}
                exec(compile(item.source, "authored-selected.py", "exec"), namespace)
                self.assertEqual(namespace["message"](), f"a{separator}b")

    def test_real_git_zero_context_hunks_keep_method_and_function_lines(self):
        entries = []
        observations["git_zero_context"] = entries
        with tempfile.TemporaryDirectory(prefix="testpilot-physical-git-") as temporary:
            root = Path(temporary)
            for index, separator in enumerate(SEPARATORS):
                with self.subTest(separator=ascii(separator)):
                    before = "\r\n".join((
                        "class Box:", "    @staticmethod", "    def token():",
                        f'        return "old{separator}tail"', "",
                        "def marker():", f'    return "old2{separator}tail"', ""))
                    after = before.replace('"old', '"new')
                    compile(after, "sample.py", "exec")
                    repo = root / str(index)
                    diff = modified_repo(repo, before, after)
                    parsed = parse_unified_diff(diff)
                    selected = changed_functions(repo, diff)
                    actual = [(item.qualname, item.lineno, item.end_lineno,
                               item.changed_lines, item.is_method) for item in selected]
                    entries.append({"separator": ascii(separator),
                                    "added_lines": sorted(parsed[0].added_lines),
                                    "selected": actual, "diff": diff})
                    self.assertEqual(parsed[0].added_lines, {4, 7})
                    self.assertEqual(actual, [
                        ("Box.token", 2, 4, [4], True), ("marker", 6, 7, [7], False)])
                    self.assertEqual(selected[0].import_name, "Box")
                    self.assertEqual(selected[1].import_name, "marker")
                    for item in selected:
                        ast.parse(textwrap.dedent(item.source))
                    self.assertIn(f'"new{separator}tail"', selected[0].source)

    def test_real_consumer_sends_complete_decorated_source_to_planner(self):
        with tempfile.TemporaryDirectory(prefix="testpilot-physical-consumer-") as temporary:
            root = Path(temporary)
            repo = root / "repo"
            before = (
                "def keep(fn):\n    return fn\n\n"
                "@keep\n"
                "def stamp(value):\n"
                '    """left\u2028middle\u2029right"""\n'
                '    marker = "one\x85two"\n'
                "    return marker + value\n")
            after = before.replace("return marker + value\n", 'return marker + value + "!"\n')
            existing = ("from sample import stamp\n\n"
                        "def test_existing_prefix():\n    assert stamp('seed').startswith('one')\n")
            diff = modified_repo(repo, before, after, existing)
            expected_source = after[after.index("@keep\n"):].removesuffix("\n")
            expected_value = ascii("one\x85twoX!")
            generated = ("from sample import stamp\n\n"
                         f"def test_generated_stamp():\n    assert stamp('X') == {expected_value}\n")
            fence = chr(96) * 3
            prompts = []

            def reply(model, messages):
                prompts.append({"model": model, "user": messages[-1]["content"]})
                if len(prompts) == 1:
                    return "Exercise the changed stamp suffix while preserving its marker."
                return fence + "python path=tests/test_generated_stamp.py\n" + generated + fence

            client = ScriptedModel(reply)
            result = TestPilot(client, RoutingConfig("review-plan", "review-edit"),
                               coverage=False, timeout_s=30, max_repair_rounds=0).run(repo, diff)
            patch_path = root / "generated.patch"
            patch_path.write_text(result.patch, encoding="utf-8")
            apply = subprocess.run(["git", "-C", str(repo), "apply", "--check", str(patch_path)],
                                   capture_output=True, text=True)
            unchanged = ((repo / "sample.py").read_bytes() == after.encode("utf-8")
                         and (repo / "tests/test_existing.py").read_bytes() == existing.encode("utf-8")
                         and not (repo / "tests/test_generated_stamp.py").exists())
            selected = result.changed_functions
            exact_prompt = bool(prompts and expected_source in prompts[0]["user"])
            observation = {
                "status": result.status, "tests_written": result.tests_written,
                "final": result.final, "planner_source_exact": exact_prompt,
                "selected": selected, "prompts": prompts, "patch": result.patch,
                "git_apply_check": apply.returncode, "git_apply_stderr": apply.stderr,
                "originals_unchanged": unchanged, "expected_source": expected_source}
            observations["consumer"] = observation
            self.assertEqual(result.status, "passed")
            self.assertEqual(result.tests_written, 1)
            self.assertEqual(result.final["passed"], 2)
            self.assertEqual(len(prompts), 2)
            self.assertTrue(unchanged)
            self.assertEqual(apply.returncode, 0, apply.stderr)
            self.assertEqual([(item["qualname"], item["lineno"], item["end_lineno"],
                               item["changed_lines"]) for item in selected], [("stamp", 4, 8, [8])])
            self.assertTrue(exact_prompt, observation)
            self.assertEqual(selected[0]["source"], expected_source)


def pin(path):
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}


suite = unittest.defaultTestLoader.loadTestsFromTestCase(PhysicalLineReceiving)
result = unittest.TextTestRunner(verbosity=2).run(suite)
receipt = {"source": str(SOURCE), "python": sys.version, "harness": pin(Path(__file__)),
           "package": {path.name: pin(path) for path in sorted((SOURCE / "testpilot").glob("*.py"))},
           "tests_run": result.testsRun, "failures": len(result.failures),
           "errors": len(result.errors), "skips": len(result.skipped),
           "successful": result.wasSuccessful(), "observations": observations}
RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"receipt": str(RECEIPT), "tests_run": result.testsRun,
                  "failures": len(result.failures), "errors": len(result.errors),
                  "successful": result.wasSuccessful()}))
raise SystemExit(0 if result.wasSuccessful() else 1)
