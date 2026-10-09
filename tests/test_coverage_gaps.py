"""Focused standard-library tests for the saved coverage-gap reader."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from testpilot.coverage_gaps import ReportError, analyze_report, read_report

SOURCE = Path(__file__).resolve().parents[1]
FIXTURE = SOURCE / "tests" / "fixtures" / "coverage_gaps_report.json"


class CoverageGapsTests(unittest.TestCase):
    def fixture(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def run_cli(self, root, report, *args):
        env = dict(os.environ, PYTHONPATH=str(SOURCE), PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([sys.executable, "-B", "-m", "testpilot.coverage_gaps",
                               "--report", str(report), *args], cwd=root, env=env,
                              capture_output=True, timeout=10)

    def test_missing_added_lines_and_unique_denominator(self):
        result = analyze_report(self.fixture())
        self.assertEqual(result["summary"], {
            "unique_changed_lines": 6, "executed_changed_lines": 1,
            "missing_changed_lines": 3, "not_represented_changed_lines": 2,
            "unknown_changed_lines": 0, "known_executable_changed_lines": 4,
            "known_executable_changed_line_percent": 25.0,
        })
        calc = next(x for x in result["files"] if x["path"] == "calc.py")
        self.assertEqual([(x["line"], x["state"]) for x in calc["lines"]],
                         [(3, "executed"), (4, "missing"), (7, "not_represented"), (9, "missing")])
        self.assertEqual(calc["lines"][1]["function_ordinals"], [0, 1])

    def test_function_ordinals_deletion_and_duplicates_preserved(self):
        report = self.fixture()
        result = analyze_report(report)
        self.assertEqual([x["ordinal"] for x in result["functions"]], [0, 1, 2, 3, 4])
        self.assertEqual(result["functions"][0]["changed_lines"], [3, 4, 7])
        self.assertEqual(result["functions"][2]["changed_lines"], [])
        self.assertEqual(report, self.fixture())

    def test_exact_path_join_and_literal_unicode_backslash(self):
        result = analyze_report(self.fixture())
        paths = [x["path"] for x in result["files"]]
        self.assertEqual(paths, sorted(["Calc.py", "calc.py", "Δ\\literal.py"]))
        upper = next(x for x in result["files"] if x["path"] == "Calc.py")
        self.assertEqual(upper["coverage_state"], "not_represented")
        self.assertEqual(upper["lines"][0]["state"], "not_represented")

    def test_unavailable_is_not_zero_or_missing(self):
        for final in (None, {}, {"coverage": None}):
            report = self.fixture()
            report["final"] = final
            result = analyze_report(report)
            self.assertEqual(result["coverage_state"], "unavailable")
            self.assertEqual(result["summary"]["unknown_changed_lines"], 6)
            for key in ("executed_changed_lines", "missing_changed_lines",
                        "not_represented_changed_lines", "known_executable_changed_lines",
                        "known_executable_changed_line_percent"):
                self.assertIsNone(result["summary"][key])
        report = self.fixture()
        del report["final"]
        self.assertEqual(analyze_report(report)["summary"]["unknown_changed_lines"], 6)

    def test_empty_population_known_and_unavailable_are_distinct(self):
        for final, expected in ((None, None), ({"coverage": {"files": {}}}, 0)):
            result = analyze_report({"changed_functions": [], "final": final})
            self.assertEqual(result["summary"]["unique_changed_lines"], 0)
            self.assertEqual(result["summary"]["known_executable_changed_lines"], expected)
            self.assertIsNone(result["summary"]["known_executable_changed_line_percent"])

    def test_final_only_never_round_or_aggregate_coverage(self):
        report = self.fixture()
        report["coverage"] = {"changed_lines_after": 0}
        report["rounds"][0]["result"]["coverage"]["files"]["calc.py"]["executed"] = [4, 7, 9]
        self.assertEqual(analyze_report(report)["summary"]["missing_changed_lines"], 3)

    def test_malformed_known_shape_refused(self):
        for final in (False, [], {"coverage": []}, {"coverage": {}},
                      {"coverage": {"files": []}},
                      {"coverage": {"files": {"calc.py": None}}},
                      {"coverage": {"files": {"calc.py": {"executed": [], "missing": None}}}}):
            report = self.fixture()
            report["final"] = final
            with self.assertRaises(ReportError):
                analyze_report(report)

    def test_strict_line_labels_and_span(self):
        for number in (True, False, 0, -1, 3.0, "3", 11):
            report = self.fixture()
            report["changed_functions"][0]["changed_lines"] = [number]
            with self.assertRaises(ReportError):
                analyze_report(report)
        report = self.fixture()
        report["final"]["coverage"]["files"]["calc.py"]["executed"] = [True]
        with self.assertRaises(ReportError):
            analyze_report(report)

    def test_coverage_conflict_even_outside_selected_lines(self):
        report = self.fixture()
        report["final"]["coverage"]["files"]["calc.py"]["missing"].append(1)
        with self.assertRaises(ReportError):
            analyze_report(report)

    def test_budget_before_deduplication_and_association_expansion(self):
        report = self.fixture()
        report["changed_functions"][0]["changed_lines"] = [3] * 100001
        with self.assertRaises(ReportError):
            analyze_report(report)
        function = dict(report["changed_functions"][0], changed_lines=[3] * 25)
        report["changed_functions"] = [function] * 4001
        with self.assertRaises(ReportError):
            analyze_report(report)
        report = self.fixture()
        report["final"]["coverage"]["files"]["calc.py"]["executed"] = [1] * 100001
        with self.assertRaises(ReportError):
            analyze_report(report)

    def test_public_api_enforces_serialized_output_cap(self):
        label = "é" * 4096
        function = {"path": label, "qualname": "target", "lineno": 1,
                    "end_lineno": 1, "changed_lines": [1]}
        report = {"changed_functions": [function] * 700, "final": None}
        self.assertLess(len(json.dumps(report, ensure_ascii=False).encode("utf-8")),
                        8 * 1024 * 1024)
        with self.assertRaises(ReportError):
            analyze_report(report)

    def test_json_integer_conversion_refuses_before_output(self):
        limit = sys.get_int_max_str_digits()
        if not limit:
            self.skipTest("runtime integer conversion limit is disabled")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = root / "report.json"
            raw = ('{"changed_functions":[],"extra":1' + "0" * limit + "}").encode()
            report.write_bytes(raw)
            target = root / "must-not-exist.json"
            result = self.run_cli(root, report, "--output", str(target))
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertNotIn(b"Traceback", result.stderr)
            self.assertFalse(target.exists())
            self.assertEqual(report.read_bytes(), raw)
        self.assertEqual(sys.get_int_max_str_digits(), limit)

    def test_api_integer_conversion_is_report_error(self):
        limit = sys.get_int_max_str_digits()
        if not limit:
            self.skipTest("runtime integer conversion limit is disabled")
        huge = 10 ** limit
        report = {"changed_functions": [{"path": "x.py", "qualname": "f",
                  "lineno": huge, "end_lineno": huge, "changed_lines": []}],
                  "final": None}
        with self.assertRaises(ReportError):
            analyze_report(report)
        self.assertEqual(sys.get_int_max_str_digits(), limit)

    def test_input_json_admission(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "invalid.json"
            for payload in (b'{"changed_functions":[],"changed_functions":[]}',
                            b'{"changed_functions":[],"extra":NaN}', b'\xff'):
                path.write_bytes(payload)
                with self.assertRaises(ReportError):
                    read_report(path)
            path.write_bytes(b" " * (8 * 1024 * 1024 + 1))
            with self.assertRaises(ReportError):
                read_report(path)

    def test_real_cli_exact_input_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = root / "report.json"
            raw = FIXTURE.read_bytes()
            report.write_bytes(raw)
            target = root / "gaps.json"
            result = self.run_cli(root, report, "--output", str(target))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(target.read_bytes()), analyze_report(self.fixture()))
            self.assertEqual(report.read_bytes(), raw)
            sentinel = target.read_bytes()
            existing = self.run_cli(root, report, "--output", str(target))
            self.assertNotEqual(existing.returncode, 0)
            self.assertEqual(target.read_bytes(), sentinel)
            alias = self.run_cli(root, report, "--output", str(report))
            self.assertNotEqual(alias.returncode, 0)
            self.assertEqual(report.read_bytes(), raw)

    def test_real_cli_stdout_missing_and_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = root / "report.json"
            report.write_bytes(FIXTURE.read_bytes())
            result = self.run_cli(root, report)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), analyze_report(self.fixture()))
            missing = self.run_cli(root, root / "missing.json")
            self.assertNotEqual(missing.returncode, 0)
            report.write_bytes(b'{"changed_functions":false}')
            invalid = self.run_cli(root, report, "--output", str(root / "must-not-exist.json"))
            self.assertEqual(invalid.returncode, 2)
            self.assertFalse((root / "must-not-exist.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
