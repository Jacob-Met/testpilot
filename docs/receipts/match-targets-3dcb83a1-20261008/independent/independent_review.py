"""Independent AST and real pipeline review of match/case target discovery."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
PACKAGE = Path(os.environ["TESTPILOT_REVIEW_SOURCE"]).resolve()
sys.path.insert(0, str(PACKAGE))
sys.dont_write_bytecode = True
from testpilot.diff import changed_functions, functions_touching
from testpilot.loop import TestPilot
from testpilot.model import RoutingConfig, ScriptedModel

METRICS = {}
FENCE = chr(96) * 3
SOURCE = '''MODE = "fast"
match MODE:
    case "fast":
        class Scale:
            @staticmethod
            def times(value):
                match value:
                    case 0:
                        return 0
                    case _:
                        return value * 2
    case _:
        class Fallback:
            def times(self, value):
                return value
'''
def marked_line(source, text):
    matches = [i for i, line in enumerate(source.splitlines(), 1) if text in line]
    if len(matches) != 1:
        raise ValueError("ambiguous test marker " + text)
    return matches[0]

class IndependentMatchReview(unittest.TestCase):
    def test_match_nested_class_method_keeps_decorator_identity_and_line(self):
        source = SOURCE.replace("return value * 2", "return value * 3")
        line = marked_line(source, "return value * 3")
        found = functions_touching(source, "src/pkg/scale.py", {line}, {line})
        METRICS["method"] = [f.to_dict() for f in found]
        self.assertEqual([f.qualname for f in found], ["Scale.times"])
        target = found[0]
        self.assertEqual((target.module, target.import_name, target.is_method),
                         ("pkg.scale", "Scale", True))
        self.assertEqual((target.lineno, target.end_lineno, target.changed_lines),
                         (5, 11, [11]))
        self.assertEqual(target.source,
                         "\n".join(source.splitlines()[4:11]))

    def test_two_case_definitions_with_same_name_preserve_separate_source_spans(self):
        source = '''match dangerous_subject():
    case "a" if dangerous_guard():
        def selected():
            return "a"
    case _:
        def selected():
            return "b"
'''
        targets = functions_touching(source, "chooser.py", {4, 7}, {4, 7})
        METRICS["duplicate_names"] = [t.to_dict() for t in targets]
        self.assertEqual([(t.qualname, t.lineno, t.end_lineno, t.changed_lines)
                          for t in targets],
                         [("selected", 3, 4, [4]), ("selected", 6, 7, [7])])
        self.assertTrue(all(t.import_name == "selected" and not t.is_method
                            for t in targets))

    def test_function_local_match_keeps_enclosing_target(self):
        source = '''def enclosing(mode):
    match mode:
        case "a":
            class Local:
                def nested(self):
                    return 4
            return Local().nested()
    return 0
'''
        targets = functions_touching(source, "nest.py", {6}, {6})
        METRICS["enclosing"] = [t.to_dict() for t in targets]
        self.assertEqual([(t.qualname, t.lineno, t.end_lineno, t.changed_lines)
                          for t in targets], [("enclosing", 1, 8, [6])])
        self.assertFalse(targets[0].is_method)

    def test_actual_git_pipeline_keeps_existing_test_and_generates_for_method(self):
        with tempfile.TemporaryDirectory(prefix="git-consumer-", dir=ROOT) as temp:
            repo = Path(temp)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            source_path = repo / "scale.py"
            source_path.write_text(SOURCE)
            tests = repo / "tests"
            tests.mkdir()
            sentinel = tests / "test_scale.py"
            sentinel.write_text("def test_existing_sentinel():\n    assert 19 == 19\n")
            subprocess.run(["git", "add", "--", "scale.py", "tests/test_scale.py"],
                           cwd=repo, check=True)
            after = SOURCE.replace("return value * 2", "return value * 3")
            source_path.write_text(after)
            original = {str(p.relative_to(repo)): p.read_bytes()
                        for p in (source_path, sentinel)}
            diff = subprocess.check_output([
                "git", "-c", "color.ui=false", "diff", "--no-ext-diff",
                "--unified=0", "--", "scale.py"], cwd=repo, text=True)
            model = ScriptedModel([
                "Test the active class method for nonzero and zero values.",
                FENCE + "python path=tests/test_scale.py\n"
                "from scale import Scale\n\n"
                "def test_times_positive():\n    assert Scale.times(3) == 9\n\n"
                "def test_times_zero():\n    assert Scale.times(0) == 0\n" + FENCE])
            report = TestPilot(model, RoutingConfig(planner_model="fixture-plan",
                editor_model="fixture-editor"), coverage=False,
                timeout_s=30, max_repair_rounds=0).run(repo, diff)
            written = repo / "generated.patch"
            written.write_text(report.patch)
            patch_check = subprocess.run(["git", "apply", "--check", str(written)],
                cwd=repo, capture_output=True, text=True)
            unchanged = all((repo / rel).read_bytes() == raw
                            for rel, raw in original.items())
            METRICS["pipeline"] = {
                "status": report.status, "tests_written": report.tests_written,
                "final_passed": report.final.get("passed") if report.final else None,
                "selected": [f["qualname"] for f in report.changed_functions],
                "model_calls": [c[0] for c in model.calls],
                "generated_files": sorted(report.test_files),
                "git_apply_check_returncode": patch_check.returncode,
                "original_source_and_existing_tests_unchanged": unchanged,
                "fixture_generated_test_absent": not
                    (tests / "test_scale_testpilot.py").exists()}
            self.assertEqual(report.status, "passed", METRICS["pipeline"])
            self.assertEqual(report.tests_written, 2)
            self.assertEqual(report.final["passed"], 3)
            self.assertEqual(METRICS["pipeline"]["selected"], ["Scale.times"])
            self.assertEqual(METRICS["pipeline"]["model_calls"],
                             ["fixture-plan", "fixture-editor"])
            self.assertEqual(sorted(report.test_files), ["tests/test_scale_testpilot.py"])
            self.assertIn("from scale import Scale", model.calls[0][1][1]["content"])
            self.assertEqual(patch_check.returncode, 0, patch_check.stderr)
            self.assertTrue(unchanged)
            self.assertFalse((tests / "test_scale_testpilot.py").exists())

if __name__ == "__main__":
    manifest = {str(p.relative_to(PACKAGE)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((PACKAGE / "testpilot").glob("*.py"))}
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(IndependentMatchReview))
    unchanged = all(hashlib.sha256((PACKAGE / p).read_bytes()).hexdigest() == digest
                    for p, digest in manifest.items())
    receipt = {"package": str(PACKAGE), "source_hashes": manifest,
        "sources_unchanged": unchanged, "python": sys.version,
        "optimized": bool(sys.flags.optimize),
        "test_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "tests": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "status": "pass" if result.wasSuccessful() else "fail",
        "metrics": METRICS}
    print(json.dumps(receipt, sort_keys=True))
    if destination := os.environ.get("TESTPILOT_REVIEW_RECEIPT"):
        Path(destination).write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
