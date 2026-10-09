"""Native Windows review exports preserve complete bytes and refuse replacement."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from testpilot import export_tests as export

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(sys.platform == "win32", "Windows publication semantics")
class WindowsExportTests(unittest.TestCase):
    def setUp(self):
        retained = os.environ.get("TESTPILOT_WINDOWS_TEST_ARTIFACTS")
        self.temporary = None
        if retained:
            self.root = Path(retained) / self._testMethodName
            self.root.mkdir(parents=True, exist_ok=False)
        else:
            self.temporary = tempfile.TemporaryDirectory(prefix="testpilot-win-export-")
            self.root = Path(self.temporary.name)

    def tearDown(self):
        if self.temporary:
            self.temporary.cleanup()

    def report(self, name="input.json", text=None):
        document = {
            "status": "suspected_code_bug",
            "test_files": text if text is not None else {
                "tests/nested/test_literal.py": "# café λ\r\ntext = '雪'\r# final",
                "tests/test_empty.py": "",
                "tests/test_bom.py": "\ufeff# retained BOM\n",
            },
            "rounds": [{"test_files": {"tests/test_old.py": "historical only"}}],
            "unknown_metadata": {"literal": "</script>\nreview only"},
        }
        data = (json.dumps(document, ensure_ascii=False, indent=2) + "\r\n").encode("utf-8")
        p = self.root / name
        p.write_bytes(data)
        return p, data, document

    def no_stages(self):
        self.assertEqual(list(self.root.glob(".testpilot-export-*")), [])

    def exact_output(self, out, report, raw, document):
        payloads = {name: text.encode("utf-8")
                    for name, text in document["test_files"].items()}
        expected = {
            "schema": "testpilot.export-tests/1",
            "status": "exported_for_review",
            "source_report": {
                "path": str(report.absolute()), "sha256": digest(raw),
                "recorded_status": document.get("status"), "copy": "source-report.json",
            },
            "test_files": [
                {"path": name, "bytes": len(payloads[name]), "sha256": digest(payloads[name])}
                for name in sorted(payloads)
            ],
            "test_runs": 0,
            "model_calls": 0,
            "scope": "Exact admitted final test bytes for review; historical status is not a new execution result.",
        }
        payloads["source-report.json"] = raw
        payloads["export-manifest.json"] = (
            json.dumps(expected, indent=2, ensure_ascii=True) + "\n").encode()
        actual = {p.relative_to(out).as_posix(): p.read_bytes()
                  for p in out.rglob("*") if p.is_file()}
        self.assertEqual(actual, payloads)
        self.assertEqual(json.loads(actual["export-manifest.json"]), expected)
        self.assertEqual(report.read_bytes(), raw)
        self.no_stages()
        return expected

    def test_complete_literal_bytes(self):
        report, raw, document = self.report()
        out = self.root / "review café 雪"
        result = export.export_saved_tests(report, out)
        self.assertEqual(result, self.exact_output(out, report, raw, document))

    def test_existing_destinations_are_unchanged(self):
        report, raw, _ = self.report()
        for kind in ("file", "empty", "nonempty"):
            out = self.root / kind
            if kind == "file":
                out.write_bytes(b"retained file")
            else:
                out.mkdir()
                if kind == "nonempty":
                    (out / "retained").write_bytes(b"retained child")
            before = (out.stat().st_dev, out.stat().st_ino)
            with self.assertRaises(export.ExportTestsError):
                export.export_saved_tests(report, out)
            self.assertEqual((out.stat().st_dev, out.stat().st_ino), before)
            if kind == "file":
                self.assertEqual(out.read_bytes(), b"retained file")
            elif kind == "empty":
                self.assertEqual(list(out.iterdir()), [])
            else:
                self.assertEqual({p.name: p.read_bytes() for p in out.iterdir()},
                                 {"retained": b"retained child"})
            self.assertEqual(report.read_bytes(), raw)
            self.no_stages()

    def test_empty_destination_created_after_staging_is_preserved(self):
        report, raw, _ = self.report()
        out = self.root / "late destination"
        original_write = export._write_bytes
        observed = []

        def create_after_complete_stage(path, data):
            original_write(path, data)
            if path.name == "export-manifest.json":
                out.mkdir()
                observed.append((out.stat().st_dev, out.stat().st_ino))

        with patch.object(export, "_write_bytes", create_after_complete_stage):
            with self.assertRaises(export.ExportTestsError):
                export.export_saved_tests(report, out)
        self.assertEqual(len(observed), 1)
        self.assertEqual((out.stat().st_dev, out.stat().st_ino), observed[0])
        self.assertEqual(list(out.iterdir()), [])
        self.assertEqual(report.read_bytes(), raw)
        self.no_stages()

    def test_write_failure_removes_only_private_stage(self):
        report, raw, _ = self.report()
        neighbour = self.root / "neighbour"
        neighbour.write_bytes(b"keep neighbour")
        out = self.root / "review"
        original_write = export._write_bytes

        def fail_before_report_copy(path, data):
            if path.name == "source-report.json":
                raise OSError("authored Windows prepublication write failure")
            original_write(path, data)

        with patch.object(export, "_write_bytes", fail_before_report_copy):
            with self.assertRaisesRegex(export.ExportTestsError, "authored Windows"):
                export.export_saved_tests(report, out)
        self.assertFalse(out.exists())
        self.assertEqual(report.read_bytes(), raw)
        self.assertEqual(neighbour.read_bytes(), b"keep neighbour")
        self.no_stages()

    def test_missing_parent_and_invalid_report_refuse(self):
        report, raw, _ = self.report()
        with self.assertRaises(export.ExportTestsError):
            export.export_saved_tests(report, self.root / "missing" / "review")
        bad = self.root / "bad.json"
        bad.write_bytes(b'{"test_files": {}}')
        with self.assertRaises(export.ExportTestsError):
            export.export_saved_tests(bad, self.root / "invalid review")
        self.assertFalse((self.root / "missing").exists())
        self.assertFalse((self.root / "invalid review").exists())
        self.assertEqual(report.read_bytes(), raw)
        self.assertEqual(bad.read_bytes(), b'{"test_files": {}}')
        self.no_stages()

    def test_two_native_publishers_have_one_complete_winner(self):
        one = self.report("one.json", {"tests/test_one.py": "# first complete input\n"})
        two = self.report("two.json", {"tests/test_two.py": "# second complete input\r\n"})
        out = self.root / "contended"
        gate = self.root / "release"
        program = (
            "import sys,pathlib,time,json\n"
            "sys.path.insert(0,sys.argv[1])\n"
            "from testpilot import export_tests as e\n"
            "real=e._directory_publisher\n"
            "def delayed():\n"
            " publish=real()\n"
            " def wait_publish(stage,out):\n"
            "  pathlib.Path(sys.argv[4]).write_bytes(b'ready')\n"
            "  end=time.monotonic()+5\n"
            "  while not pathlib.Path(sys.argv[5]).exists():\n"
            "   if time.monotonic()>end: raise TimeoutError('authored barrier expired')\n"
            "   time.sleep(0.01)\n"
            "  publish(stage,out)\n"
            " return wait_publish\n"
            "e._directory_publisher=delayed\n"
            "try:\n"
            " m=e.export_saved_tests(sys.argv[2],sys.argv[3]);print(json.dumps({'ok':True,'manifest':m}))\n"
            "except e.ExportTestsError as x:\n"
            " print(json.dumps({'ok':False,'error':str(x)}));sys.exit(2)\n"
        )
        children = []
        try:
            for i, item in enumerate((one, two)):
                args = [sys.executable, "-I", "-S", "-B", "-c", program,
                        str(ROOT), str(item[0]), str(out),
                        str(self.root / ("ready%d" % i)), str(gate)]
                children.append(subprocess.Popen(
                    args, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
            end = time.monotonic() + 5
            while not all((self.root / ("ready%d" % i)).is_file() for i in (0, 1)):
                self.assertLess(time.monotonic(), end, "both actual stages must reach publication")
                self.assertTrue(all(p.poll() is None for p in children))
                time.sleep(0.01)
            gate.write_bytes(b"publish")
            results = []
            for i, p in enumerate(children):
                stdout, stderr = p.communicate(timeout=5)
                (self.root / ("child%d.stdout.bin" % i)).write_bytes(stdout)
                (self.root / ("child%d.stderr.bin" % i)).write_bytes(stderr)
                self.assertEqual(stderr, b"")
                results.append((p.returncode, json.loads(stdout)))
            self.assertEqual(sorted(r[0] for r in results), [0, 2])
            winner = next(i for i, r in enumerate(results) if r[0] == 0)
            report, raw, document = (one, two)[winner]
            self.assertEqual(results[winner][1]["manifest"],
                             self.exact_output(out, report, raw, document))
            self.assertFalse(results[1-winner][1]["ok"])
            for report, raw, _ in (one, two):
                self.assertEqual(report.read_bytes(), raw)
            (self.root / "contention-result.json").write_text(
                json.dumps({"winner": winner, "children": [
                    {"pid": p.pid, "exit": r[0], "result": r[1]}
                    for p, r in zip(children, results)]}, indent=2), encoding="utf-8")
        finally:
            for p in children:
                if p.poll() is None:
                    p.kill()
                p.wait(timeout=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
