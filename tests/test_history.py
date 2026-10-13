"""Read-only saved-report finding: literal results, partialness and finite work."""
from __future__ import annotations

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

from testpilot import history
from testpilot import __main__ as cli

ROOT = Path(__file__).resolve().parents[1]


def final_record():
    return {"returncode": 0, "timed_out": False, "ok": True,
            "duration_s": 0.25, "output": "private runner tail", "summary": "1 passed",
            "passed": 1, "failed": 0, "errors": 0, "skipped": 0,
            "cases": [], "coverage": None}


def generation():
    return {"status": "passed", "changed_functions": [{
        "path": "src/CAFÉ.py", "qualname": "Thing.Δ", "source": "raise RuntimeError('never execute')",
        "lineno": 3, "end_lineno": 4, "changed_lines": [3]}],
        "repair_rounds_used": 0, "max_repair_rounds": 2,
        "test_files": {"tests/z.py": "raise SystemExit('never execute')", "tests/a.py": "opaque"},
        "tests_written": 1, "final": final_record(), "patch": "private patch",
        "coverage": None, "ledger": {}, "rounds": [], "plan": "private plan", "message": "private message"}


def recheck():
    return {"schema": "testpilot.recheck/1", "status": "no_tests", "ok": False,
            "repo": "../recorded-only", "python": "missing-interpreter", "started_at": "later?", "finished_at": "earlier?",
            "source_report": {"path": "/missing/report.json", "sha256": "recorded hash", "recorded_status": "failed"},
            "test_files": {"tests/retained_雪.py": "private retained source"},
            "retained_tests": [{"path": "tests/retained_雪.py", "sha256": "literal", "bytes": 0, "placement": "retained"}],
            "final": final_record(), "model_calls": 0, "scope": "authored test record"}


def saved(path, value, *, bom=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = (b"\xef\xbb\xbf" if bom else b"") + (json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(body)
    return body


def snapshot(root):
    out = {}
    for path in sorted(root.rglob("*")):
        st = path.lstat()
        out[path.relative_to(root).as_posix()] = (st.st_mode, path.read_bytes() if path.is_file() and not path.is_symlink() else None)
    return out


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="testpilot-history-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def invoke(self, *arguments):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TESTPILOT_BACKEND="history-must-not-build-a-model")
        return subprocess.run([sys.executable, "-B", "-m", "testpilot", "history", "--root", str(self.root), *arguments],
                              cwd=ROOT, env=env, capture_output=True, timeout=15)

    def test_native_generation_and_recheck_are_literal_and_read_only(self):
        original = ROOT / "eval/results/calc_clamp/report.json"
        (self.root / "report.json").write_bytes(original.read_bytes())
        body = saved(self.root / "rechecked/recheck.json", recheck(), bom=True)
        before = snapshot(self.root)
        result = history.scan_history(self.root)
        self.assertTrue(result["complete"])
        self.assertEqual([r["path"] for r in result["runs"]], ["rechecked/recheck.json", "report.json"])
        row = result["runs"][0]
        self.assertEqual(row["sha256"], hashlib.sha256(body).hexdigest())
        self.assertEqual(row["bytes"], len(body))
        self.assertEqual(row["recheck_context"]["started_at"], "later?")
        self.assertEqual(row["recheck_context"]["source_report"], recheck()["source_report"])
        self.assertIsNone(row["final"]["junit_available"])
        self.assertEqual(row["test_paths"], ["tests/retained_雪.py"])
        self.assertEqual(result["counts"]["admitted"], 2)
        self.assertEqual(snapshot(self.root), before)

    def test_schema_decides_kind_and_null_final_is_generation_only(self):
        g = generation(); g["final"] = None; g["schema"] = None
        saved(self.root / "recheck.json", g)
        result = history.scan_history(self.root)
        self.assertEqual(result["runs"][0]["kind"], "generation")
        self.assertIsNone(result["runs"][0]["final"])
        r = recheck(); r["final"] = None
        saved(self.root / "report.json", r)
        result = history.scan_history(self.root)
        self.assertEqual([(p["path"], p["code"]) for p in result["problems"]], [("report.json", "invalid_report")])

    def test_filters_are_literal_and_do_not_hide_bad_neighbors(self):
        saved(self.root / "good/report.json", generation())
        saved(self.root / "retained/recheck.json", recheck())
        (self.root / "report.json").write_bytes(b"broken JSON")
        result = history.scan_history(self.root, statuses=["passed", "passed"], query="café", kind="generation")
        self.assertFalse(result["complete"])
        self.assertEqual(result["filters"], {"statuses": ["passed", "passed"], "query": "café", "kind": "generation"})
        self.assertEqual([r["path"] for r in result["runs"]], ["good/report.json"])
        self.assertEqual(result["counts"]["admitted"], 2)
        self.assertEqual(result["counts"]["candidate_files"], 3)
        for query in ["private plan", "private runner tail", "/missing/report.json"]:
            self.assertEqual(history.scan_history(self.root, query=query)["runs"], [])
        self.assertEqual(len(history.scan_history(self.root, query="retained_雪")["runs"]), 1)
        self.assertEqual(len(history.scan_history(self.root, query="")["runs"]), 2)

    def test_depth_zero_default_and_eight(self):
        for name in ["report.json", "a/report.json", "a/b/report.json"]:
            saved(self.root / name, generation())
        for depth, expected in [(0, ["report.json"]), (1, ["a/report.json", "report.json"]),
                                (8, ["a/b/report.json", "a/report.json", "report.json"])]:
            result = history.scan_history(self.root, max_depth=depth)
            self.assertTrue(result["complete"])
            self.assertEqual([r["path"] for r in result["runs"]], expected)

    @unittest.skipUnless(hasattr(os, "symlink") and hasattr(os, "mkfifo"), "requires POSIX links and FIFO")
    def test_internal_links_are_skipped_and_fifo_never_opened(self):
        saved(self.root / "actual/report.json", generation())
        (self.root / "report.json").symlink_to(self.root / "actual/report.json")
        (self.root / "cycle").symlink_to(self.root, target_is_directory=True)
        os.mkfifo(self.root / "recheck.json")
        result = history.scan_history(self.root, max_depth=8)
        self.assertEqual([r["path"] for r in result["runs"]], ["actual/report.json"])
        self.assertEqual([(p["path"], p["code"]) for p in result["problems"]], [("recheck.json", "read_error")])
        self.assertEqual(result["counts"]["candidate_files"], 2)
        explicit = self.root.parent / (self.root.name + "-link")
        explicit.symlink_to(self.root, target_is_directory=True)
        self.addCleanup(explicit.unlink)
        self.assertEqual(history.scan_history(explicit)["root"], str(self.root.resolve()))

    def test_candidate_named_directory_and_other_names(self):
        saved(self.root / "report.json/recheck.json", generation())
        saved(self.root / "ignored.json", generation())
        result = history.scan_history(self.root)
        self.assertEqual([r["path"] for r in result["runs"]], ["report.json/recheck.json"])
        self.assertEqual(result["counts"]["candidate_files"], 1)
        self.assertEqual(result["counts"]["entries_seen"], 3)

    def test_strict_json_failures_and_unsupported_schema(self):
        cases = [(b'{"x":1,"x":2}', "invalid_json"), (b'{"x":NaN}', "invalid_json"),
                 (b'{"nested":[1e999]}', "invalid_json"), (b'\xff', "invalid_json"),
                 (b'[]', "invalid_report"), (b'{"schema":"unknown"}', "unsupported_schema"),
                 (b'{}', "invalid_report")]
        for raw, code in cases:
            with self.subTest(raw=raw):
                (self.root / "report.json").write_bytes(raw)
                result = history.scan_history(self.root)
                self.assertEqual([p["code"] for p in result["problems"]], [code])
                self.assertEqual(result["counts"]["bytes_read"], len(raw))

    def test_native_core_types_exclude_booleans_and_allow_unknown_extra_fields(self):
        bad = []
        for key in ["repair_rounds_used", "max_repair_rounds", "tests_written"]:
            g = generation(); g[key] = True; bad.append(g)
        g = generation(); g["changed_functions"][0]["end_lineno"] = 2; bad.append(g)
        g = generation(); g["final"]["passed"] = False; bad.append(g)
        g = generation(); g["final"]["duration_s"] = -1; bad.append(g)
        g = generation(); g["final"]["junit_available"] = None; bad.append(g)
        for document in bad:
            with self.subTest(document=document):
                saved(self.root / "report.json", document)
                self.assertEqual(history.scan_history(self.root)["problems"][0]["code"], "invalid_report")
        good = generation(); good["extra"] = {"untouched": [1, None, "literal"]}
        saved(self.root / "report.json", good)
        self.assertTrue(history.scan_history(self.root)["complete"])

    def test_candidate_budget_excludes_only_its_overflow_file(self):
        for name in ["a", "b", "c"]:
            saved(self.root / name / "report.json", generation())
        with patch.object(history, "MAX_CANDIDATE_FILES", 2):
            result = history.scan_history(self.root)
        self.assertEqual(result["counts"]["candidate_files"], 2)
        self.assertEqual([r["path"] for r in result["runs"]], ["a/report.json", "b/report.json"])
        self.assertEqual([(p["path"], p["code"]) for p in result["problems"]], [("c/report.json", "candidate_limit")])

    def test_entry_overflow_discards_the_entire_directory(self):
        saved(self.root / "report.json", generation())
        (self.root / "a").touch(); (self.root / "z").touch()
        with patch.object(history, "MAX_DIRECTORY_ENTRIES", 2):
            result = history.scan_history(self.root)
        self.assertEqual(result["counts"]["entries_seen"], 2)
        self.assertEqual(result["counts"]["candidate_files"], 0)
        self.assertEqual(result["runs"], [])
        self.assertEqual([(p["path"], p["code"]) for p in result["problems"]], [(".", "entry_limit")])

    def test_byte_limit_exact_boundary_and_global_overflow_count(self):
        raw = saved(self.root / "a/report.json", generation())
        saved(self.root / "b/report.json", generation())
        with patch.object(history, "MAX_TOTAL_BYTES", len(raw)):
            result = history.scan_history(self.root)
        self.assertEqual(result["counts"]["bytes_read"], len(raw))
        self.assertEqual(result["counts"]["candidate_files"], 2)
        self.assertEqual([r["path"] for r in result["runs"]], ["a/report.json"])
        self.assertEqual(result["problems"][0]["code"], "total_bytes_limit")
        (self.root / "b/report.json").unlink()
        with patch.object(history, "MAX_REPORT_BYTES", len(raw)), patch.object(history, "MAX_TOTAL_BYTES", len(raw)):
            self.assertTrue(history.scan_history(self.root)["complete"])

    def test_per_file_limit_precedes_global_and_keeps_later_siblings(self):
        raw = saved(self.root / "z/report.json", generation())
        (self.root / "a").mkdir(); (self.root / "a/report.json").write_bytes(b" " * (len(raw) + 1))
        with patch.object(history, "MAX_REPORT_BYTES", len(raw)), patch.object(history, "MAX_TOTAL_BYTES", len(raw)):
            result = history.scan_history(self.root)
        self.assertEqual([p["code"] for p in result["problems"]], ["report_bytes_limit"])
        self.assertEqual([r["path"] for r in result["runs"]], ["z/report.json"])
        self.assertEqual(result["counts"]["candidate_files"], 2)
        self.assertEqual(result["counts"]["bytes_read"], len(raw))

    def test_invalid_bodies_use_global_budget_before_filters(self):
        (self.root / "a").mkdir(); (self.root / "a/report.json").write_bytes(b"bad")
        saved(self.root / "b/report.json", generation())
        with patch.object(history, "MAX_TOTAL_BYTES", 3):
            result = history.scan_history(self.root, statuses=["not a status"])
        self.assertEqual([p["code"] for p in result["problems"]], ["invalid_json", "total_bytes_limit"])
        self.assertEqual(result["counts"]["bytes_read"], 3)
        self.assertEqual(result["counts"]["candidate_files"], 2)

    def test_directory_error_discards_local_list_and_keeps_siblings(self):
        saved(self.root / "a/report.json", generation())
        saved(self.root / "b/report.json", generation())
        real = os.scandir
        class FailingScan:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def __iter__(self):
                yield type("Entry", (), {"name": "report.json"})()
                raise OSError("authored enumeration failure")
        def scanner(directory):
            return FailingScan() if Path(directory).name == "a" else real(directory)
        with patch.object(history.os, "scandir", scanner):
            result = history.scan_history(self.root)
        self.assertEqual([r["path"] for r in result["runs"]], ["b/report.json"])
        self.assertEqual(result["counts"]["entries_seen"], 4)
        self.assertEqual([(p["path"], p["code"]) for p in result["problems"]], [("a", "directory_error")])

    def test_size_change_is_a_read_problem_and_keeps_acquired_bytes(self):
        raw = saved(self.root / "report.json", generation())
        real = os.fstat; calls = []
        def metadata(fd):
            value = real(fd); calls.append(fd)
            if len(calls) == 2:
                fields = list(value); fields[6] += 1
                return os.stat_result(fields)
            return value
        with patch.object(history.os, "fstat", metadata):
            result = history.scan_history(self.root)
        self.assertEqual([p["code"] for p in result["problems"]], ["read_error"])
        self.assertEqual(result["counts"]["bytes_read"], len(raw))
        self.assertEqual(result["runs"], [])

    def test_option_admission_precedes_filesystem(self):
        bad = [{"max_depth": True}, {"max_depth": 9}, {"statuses": "passed"},
               {"statuses": [1]}, {"query": 1}, {"kind": "other"}]
        with patch.object(history.Path, "resolve", side_effect=AssertionError("filesystem touched")):
            for kwargs in bad:
                with self.subTest(kwargs=kwargs), self.assertRaises(history.HistoryError):
                    history.scan_history("missing", **kwargs)

    def test_text_escapes_controls_and_omits_executable_contents(self):
        saved(self.root / "line\nbreak 雪/report.json", generation())
        result = history.scan_history(self.root)
        text = history.render_history(result)
        self.assertTrue(text.isascii())
        self.assertIn('Run: "line\\nbreak \\u96ea/report.json"', text)
        for private in ["never execute", "private runner tail", "private patch", "private plan"]:
            self.assertNotIn(private, text)
        self.assertTrue(text.endswith(history.NOTICE + "\n"))
        self.assertEqual(text.count("Run: "), 1)

    def test_actual_cli_json_text_partial_and_no_matches(self):
        saved(self.root / "report.json", generation())
        before = snapshot(self.root)
        result = history.scan_history(self.root)
        received = self.invoke("--json")
        self.assertEqual(received.returncode, 0, received.stderr)
        self.assertEqual(received.stderr, b"")
        self.assertEqual(received.stdout, (json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode())
        received = self.invoke()
        self.assertEqual(received.returncode, 0, received.stderr)
        self.assertEqual(received.stdout.decode(), history.render_history(result))
        received = self.invoke("--status", "unknown", "--json")
        self.assertEqual(received.returncode, 0, received.stderr)
        self.assertEqual(json.loads(received.stdout)["runs"], [])
        self.assertEqual(snapshot(self.root), before)
        (self.root / "recheck.json").write_bytes(b"bad")
        received = self.invoke("--status", "unknown", "--json")
        self.assertEqual(received.returncode, 1, received.stderr)
        self.assertFalse(json.loads(received.stdout)["complete"])

    def test_actual_cli_invalid_root_and_depth_do_not_create(self):
        for arguments in [("--root", str(self.root / "absent")), ("--max-depth", "9"), ("--max-depth", "not-int")]:
            received = self.invoke(*arguments)
            self.assertEqual(received.returncode, 2)
            self.assertEqual(received.stdout, b"")
            self.assertTrue(received.stderr)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_history_dispatch_does_not_construct_a_model_or_run_tests(self):
        saved(self.root / "report.json", generation())
        with patch.object(cli, "make_client", side_effect=AssertionError("model requested")), \
             patch.object(cli.TestPilot, "run", side_effect=AssertionError("generation requested")), \
             patch.object(cli.subprocess, "run", side_effect=AssertionError("child requested")), \
             patch.object(sys, "stdout", io.StringIO()), patch.object(sys, "stderr", io.StringIO()):
            self.assertEqual(cli.main(["history", "--root", str(self.root), "--json"]), 0)

    def test_output_failure_returns_two_without_rescan_or_retry(self):
        saved(self.root / "report.json", generation())
        before = snapshot(self.root)
        class Broken:
            def __init__(self): self.writes = 0; self.flushes = 0; self.closed = False
            def write(self, value): self.writes += 1; return len(value)
            def flush(self): self.flushes += 1; raise OSError("authored flush failure")
            def close(self): self.closed = True
        broken = Broken(); errors = io.StringIO()
        with patch.object(sys, "stdout", broken), patch.object(sys, "stderr", errors):
            self.assertEqual(cli.main(["history", "--root", str(self.root)]), 2)
        self.assertEqual((broken.writes, broken.flushes, broken.closed), (1, 1, True))
        self.assertEqual(errors.getvalue(), "testpilot: cannot write saved-run history\n")
        self.assertEqual(snapshot(self.root), before)
        with patch.object(sys, "stdout", None), patch.object(sys, "stderr", None):
            self.assertEqual(cli.main(["history", "--root", str(self.root)]), 2)


if __name__ == "__main__":
    unittest.main()
