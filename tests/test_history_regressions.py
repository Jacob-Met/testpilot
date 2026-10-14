"""Opt-in literal summaries of retained paired regressions; never execute them."""
from __future__ import annotations

import copy
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

SOURCE = Path(history.__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "history_regression"
ORIGINAL = (FIXTURES / "recorded-regression.json").read_bytes()
REPLAY = (FIXTURES / "replayed-regression.json").read_bytes()


def record():
    return json.loads(ORIGINAL)


class RegressionHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="testpilot-history-regression-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def save(self, name="regression.json", value=None, raw=None):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw if raw is not None else json.dumps(value if value is not None else record(), ensure_ascii=False).encode())
        return target

    def invoke(self, *args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TESTPILOT_BACKEND="must-not-create-client")
        return subprocess.run([sys.executable, "-B", "-m", "testpilot", "history", "--root", str(self.root), *args],
                              cwd=SOURCE, env=env, capture_output=True, timeout=15)

    def test_unchanged_default_ignores_regression_filenames(self):
        self.save(raw=ORIGINAL)
        self.save("malformed/regression.json", raw=b"invalid JSON")
        result = history.scan_history(self.root)
        self.assertTrue(result["complete"])
        self.assertEqual(result["runs"], [])
        self.assertEqual(result["counts"]["candidate_files"], 0)
        self.assertEqual(result["filters"], {"statuses": [], "query": None, "kind": None})

    def test_default_still_refuses_regression_schema_under_old_filename(self):
        self.save("report.json", raw=ORIGINAL)
        result = history.scan_history(self.root)
        self.assertFalse(result["complete"])
        self.assertEqual(result["problems"][0]["code"], "unsupported_schema")

    def test_opt_in_receives_both_actual_reports_with_literal_phase_identity(self):
        self.save("original/regression.json", raw=ORIGINAL)
        self.save("replay/regression.json", raw=REPLAY)
        result = history.scan_history(self.root, include_regressions=True)
        self.assertTrue(result["complete"])
        self.assertTrue(result["filters"]["include_regressions"])
        self.assertEqual(len(result["runs"]), 2)
        for row, raw in zip(result["runs"], (ORIGINAL, REPLAY)):
            original = json.loads(raw)
            self.assertEqual((row["kind"], row["status"]), ("regression", "verified_regression"))
            self.assertEqual((row["bytes"], row["sha256"]), (len(raw), hashlib.sha256(raw).hexdigest()))
            self.assertNotIn("final", row)
            context = row["regression_context"]
            for phase in ("before", "after"):
                self.assertEqual({k: v for k, v in context[phase].items() if k != "result"},
                                 {k: v for k, v in original[phase].items() if k != "result"})
                self.assertEqual(context[phase]["result"]["summary"], original[phase]["result"]["summary"])
                self.assertNotIn("output", context[phase]["result"])
            self.assertEqual((context["before"]["result"]["passed"], context["before"]["result"]["failed"]), (2, 1))
            self.assertEqual(context["after"]["result"]["passed"], 3)
            self.assertEqual(context["comparison"], {"comparable": True, "reason": "failed_before_passed_after",
                             "witness_count": 1, "case_pair_count": 2, "unmatched_before_count": 0, "unmatched_after_count": 0})
            self.assertEqual(context["source_report"], original["source_report"])
            self.assertEqual(context["model_calls"], 0)

    def test_kind_regression_opts_in_without_flag(self):
        self.save(raw=ORIGINAL)
        self.save("report.json", raw=(SOURCE / "eval/results/calc_clamp/report.json").read_bytes())
        result = history.scan_history(self.root, kind="regression")
        self.assertEqual([r["kind"] for r in result["runs"]], ["regression"])
        self.assertTrue(result["filters"]["include_regressions"])
        self.assertEqual(result["counts"]["admitted"], 2)

    def test_recorded_status_is_not_recomputed_from_witnesses(self):
        for index, status in enumerate(("verified_regression", "not_regression", "after_failed", "inconclusive")):
            value = record(); value["status"] = status
            self.save(f"{index}/regression.json", value)
        result = history.scan_history(self.root, include_regressions=True)
        self.assertEqual([r["status"] for r in result["runs"]], ["verified_regression", "not_regression", "after_failed", "inconclusive"])
        self.assertEqual([r["regression_context"]["comparison"]["witness_count"] for r in result["runs"]], [1] * 4)

    def test_explicit_flag_false_preserves_original_generation_output(self):
        self.save("report.json", raw=(SOURCE / "eval/results/calc_clamp/report.json").read_bytes())
        before = history.scan_history(self.root)
        self.save(raw=ORIGINAL)
        after = history.scan_history(self.root, include_regressions=False)
        # Directory-entry counts naturally reflect the added ignored file.
        after["counts"]["entries_seen"] -= 1
        self.assertEqual(before, after)
        self.assertEqual(history.render_history(before), history.render_history(after))

    def test_filters_depth_and_schema_decide_kind(self):
        self.save("A/regression.json", raw=ORIGINAL)
        self.save("B/deeper/regression.json", raw=REPLAY)
        self.save("schema/report.json", raw=REPLAY)
        result = history.scan_history(self.root, include_regressions=True, statuses=["verified_regression"], query="TEST_EMG_RETAINED", max_depth=1)
        self.assertEqual([r["path"] for r in result["runs"]], ["A/regression.json", "schema/report.json"])
        self.assertEqual(len(history.scan_history(self.root, kind="regression", max_depth=2)["runs"]), 3)
        self.assertEqual(history.scan_history(self.root, kind="regression", query="private unrecorded source")["runs"], [])

    def test_core_shape_errors_are_visible_next_to_healthy_records(self):
        variants = []
        for path, value in [(('before', 'commit'), 3), (('after', 'source_bytes'), True),
                            (('comparison', 'comparable'), 1), (('comparison', 'witnesses'), None),
                            (('before', 'result'), None), (('model_calls',), -1), (('status',), 'future_unknown')]:
            bad = record(); node = bad
            for part in path[:-1]: node = node[part]
            node[path[-1]] = value; variants.append(bad)
        bad = record(); del bad['after']['tree']; variants.append(bad)
        bad = record(); bad['comparison']['witnesses'][0]['nodeid'] = None; variants.append(bad)
        bad = record(); bad['retained_tests'][0]['bytes'] = False; variants.append(bad)
        for i, bad in enumerate(variants): self.save(f"bad{i:02}/regression.json", bad)
        self.save("good/regression.json", raw=ORIGINAL)
        result = history.scan_history(self.root, include_regressions=True, statuses=['verified_regression'])
        self.assertFalse(result['complete'])
        self.assertEqual([r['path'] for r in result['runs']], ['good/regression.json'])
        self.assertEqual([p['code'] for p in result['problems']], ['invalid_report'] * len(variants))

    def test_nontext_status_values_are_report_problems_not_scanner_errors(self):
        for index, status in enumerate(([], {}, None, True, 3)):
            value = record(); value["status"] = status
            self.save(f"bad{index}/regression.json", value)
        self.save("good/regression.json", raw=ORIGINAL)
        result = history.scan_history(self.root, include_regressions=True)
        self.assertFalse(result["complete"])
        self.assertEqual([row["path"] for row in result["runs"]], ["good/regression.json"])
        self.assertEqual([problem["code"] for problem in result["problems"]], ["invalid_report"] * 5)
        self.assertTrue(all("regression" in problem["message"] for problem in result["problems"]))

    def test_existing_json_admission_rejects_duplicates_and_nonfinite(self):
        for i, raw in enumerate((b'{"schema":1,"schema":2}', b'{"x":NaN}', b'{"x":1e9999}', b'\xff', b'{}')):
            self.save(f"{i}/regression.json", raw=raw)
        result = history.scan_history(self.root, include_regressions=True)
        self.assertEqual(len(result['problems']), 5)
        self.assertFalse(result['complete'])
        self.assertEqual(result['runs'], [])

    def test_same_candidate_and_total_byte_budgets_include_regressions(self):
        self.save("a/regression.json", raw=ORIGINAL); self.save("b/regression.json", raw=REPLAY)
        with patch.object(history, 'MAX_CANDIDATE_FILES', 1):
            result = history.scan_history(self.root, include_regressions=True)
        self.assertEqual(result['counts']['candidate_files'], 1)
        self.assertIn('candidate_limit', [p['code'] for p in result['problems']])
        with patch.object(history, 'MAX_TOTAL_BYTES', len(ORIGINAL)):
            result = history.scan_history(self.root, include_regressions=True)
        self.assertEqual(result['counts']['bytes_read'], len(ORIGINAL))
        self.assertIn('total_bytes_limit', [p['code'] for p in result['problems']])
        with patch.object(history, 'MAX_REPORT_BYTES', len(ORIGINAL)-1):
            result = history.scan_history(self.root, include_regressions=True)
        self.assertEqual(result['counts']['bytes_read'], 0)
        self.assertEqual([p['code'] for p in result['problems']], ['report_bytes_limit'] * 2)

    def test_recorded_paths_and_source_strings_are_not_executed_or_opened(self):
        value = record(); value['repo'] = '/never/resolve/repo'; value['python'] = '/never/execute/python'
        value['source_report']['path'] = '/never/read/report.json'
        value['test_files'] = {'/never/open/test.py': "raise AssertionError('must not execute')"}
        selected = self.save(value=value); calls=[]; original_open=history.os.open
        def observed(path, flags, *args, **kwargs):
            calls.append(Path(path)); return original_open(path, flags, *args, **kwargs)
        with patch.object(history.os, 'open', observed), patch.object(subprocess, 'run', side_effect=AssertionError('no subprocess')):
            result = history.scan_history(self.root, kind='regression')
        self.assertTrue(result['complete']); self.assertEqual(calls, [selected])
        rendered = history.render_history(result)
        self.assertIn('Before', rendered); self.assertIn('After', rendered)
        self.assertNotIn('must not execute', rendered)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'requires POSIX FIFO')
    def test_nonregular_regression_is_not_consumed_and_links_remain_excluded(self):
        os.mkfifo(self.root/'regression.json')
        self.save('real/regression.json', raw=ORIGINAL)
        (self.root/'linked').symlink_to(self.root/'real', target_is_directory=True)
        result = history.scan_history(self.root, include_regressions=True)
        self.assertFalse(result['complete']); self.assertEqual(result['problems'][0]['code'], 'read_error')
        self.assertEqual([r['path'] for r in result['runs']], ['real/regression.json'])

    def test_flag_requires_exact_bool(self):
        for value in (0, 1, None, 'yes', []):
            with self.subTest(value=value), self.assertRaises(history.HistoryError):
                history.scan_history(self.root, include_regressions=value)

    def test_actual_cli_default_opt_in_kind_text_and_partial_exits(self):
        self.save('actual/regression.json', raw=ORIGINAL)
        default = self.invoke('--json'); self.assertEqual(default.returncode, 0)
        self.assertEqual(json.loads(default.stdout)['runs'], [])
        for args in [('--include-regressions', '--json'), ('--kind', 'regression', '--json')]:
            run = self.invoke(*args); self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stderr, b''); self.assertEqual(json.loads(run.stdout)['runs'][0]['sha256'], hashlib.sha256(ORIGINAL).hexdigest())
        text = self.invoke('--kind', 'regression'); self.assertEqual(text.returncode, 0, text.stderr)
        self.assertIn(b'Recorded regression', text.stdout); self.assertIn(b'Before', text.stdout); self.assertIn(b'After', text.stdout)
        self.save('bad/regression.json', raw=b'not JSON')
        partial = self.invoke('--include-regressions', '--json'); self.assertEqual(partial.returncode, 1)
        self.assertEqual(len(json.loads(partial.stdout)['runs']), 1)
        self.assertEqual((self.root/'actual/regression.json').read_bytes(), ORIGINAL)


if __name__ == '__main__':
    unittest.main()
