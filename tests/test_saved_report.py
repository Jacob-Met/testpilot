"""Receive the actual saved-artifact CLI without model calls or pytest runs."""
from __future__ import annotations

import base64
import copy
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from testpilot import saved_report
from testpilot.html_report import render_html_report

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.downloads = {}
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if tag == "a" and "download" in attrs:
            self.downloads[attrs["download"]] = base64.b64decode(attrs["href"].split(",", 1)[1], validate=True)


class SavedReportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="saved-review-tests-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        fixture = ROOT / "eval/results/calc_clamp"
        self.original_report = (fixture / "report.json").read_bytes()
        self.original_patch = (fixture / "testpilot.patch").read_bytes()

    def pair(self, report=None, patch_bytes=None):
        report_path = self.root / "report.json"
        patch_path = self.root / "testpilot.patch"
        report_path.write_bytes(self.original_report if report is None else report)
        patch_path.write_bytes(self.original_patch if patch_bytes is None else patch_bytes)
        return report_path, patch_path

    def cli(self, report, patch_path, out, optimized=False):
        command = [sys.executable, "-B"] + (["-O"] if optimized else [])
        command += ["-m", "testpilot.saved_report", "--report", str(report), "--patch", str(patch_path), "--out", str(out)]
        return subprocess.run(command, cwd=ROOT, capture_output=True, timeout=10)

    def receive(self, report, patch_path, out, optimized=False):
        originals = (report.read_bytes(), patch_path.read_bytes())
        process = self.cli(report, patch_path, out, optimized)
        self.assertEqual(process.returncode, 0, process.stderr.decode())
        self.assertEqual(process.stderr, b"")
        receipt = json.loads(process.stdout)
        data = out.read_bytes()
        self.assertEqual(receipt["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(receipt["bytes"], len(data))
        page = Page(data.decode("utf-8"))
        self.assertEqual(page.downloads, {"report.json": originals[0], "testpilot.patch": originals[1]})
        for name, original in zip(("report", "patch"), originals):
            self.assertEqual(receipt["sources"][name]["sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual(receipt["sources"][name]["bytes"], len(original))
        self.assertEqual((report.read_bytes(), patch_path.read_bytes()), originals)
        # The additive provenance section is the only change to native rendering.
        text = data.decode("utf-8")
        start = text.index('<section aria-labelledby="saved-pair-heading">')
        end = text.index("</section>", start) + len("</section>")
        self.assertEqual(text[:start] + text[end:], render_html_report(*originals))
        self.assertFalse(set(page.tags) & {"script", "iframe", "object", "img"})
        return receipt, data

    def refuse(self, report, patch_path, out=None):
        out = out or self.root / "refused.html"
        originals = (report.read_bytes(), patch_path.read_bytes())
        process = self.cli(report, patch_path, out)
        self.assertEqual(process.returncode, 2, process.stderr.decode())
        self.assertIn(b"cannot reopen saved report", process.stderr)
        self.assertNotIn(b"Traceback", process.stderr)
        self.assertFalse(out.exists())
        self.assertEqual((report.read_bytes(), patch_path.read_bytes()), originals)
        self.assertEqual(list(self.root.glob(".testpilot-review-*")), [])

    def test_actual_archived_fixtures_and_optimized_mode(self):
        for name in ("calc_clamp", "stats_median", "durations_parse"):
            with self.subTest(fixture=name):
                fixture = ROOT / "eval/results" / name
                report, patch_path = fixture / "report.json", fixture / "testpilot.patch"
                first, first_bytes = self.receive(report, patch_path, self.root / (name + ".html"))
                second, second_bytes = self.receive(report, patch_path, self.root / (name + "-optimized.html"), True)
                self.assertEqual(first_bytes, second_bytes)
                self.assertEqual(first["recorded_status"], json.loads(report.read_bytes())["status"])
                self.assertEqual(first["sha256"], second["sha256"])

    def test_native_newline_forms_and_empty_patch(self):
        document = json.loads(self.original_report)
        for recorded in (document["patch"], "one\r\ntwo\rthree\n", ""):
            for windows in (False, True):
                with self.subTest(recorded=repr(recorded[:20]), windows=windows):
                    document["patch"] = recorded
                    raw = json.dumps(document).encode()
                    patch_bytes = (recorded.replace("\n", "\r\n") if windows else recorded).encode()
                    report, patch_path = self.pair(raw, patch_bytes)
                    out = self.root / "newlines.html"
                    self.receive(report, patch_path, out)
                    out.unlink()
        raw = self.original_report.replace(b"\n", b"\r\n")
        report, patch_path = self.pair(raw, self.original_patch.replace(b"\n", b"\r\n"))
        receipt, _ = self.receive(report, patch_path, self.root / "windows.html")
        self.assertEqual(receipt["sources"]["patch"]["newline_form"], "native Windows newline expansion")

    def test_mismatched_pair_and_malformed_json_refuse(self):
        report, patch_path = self.pair(patch_bytes=self.original_patch + b"changed")
        self.refuse(report, patch_path)
        variants = [b"[]", b"{", b"\xff", b'{"status":"passed","status":"failed"}',
                    b'{"unused":{"same":1,"same":2}}']
        for token in (b"NaN", b"Infinity", b"-Infinity", b"1e999", b"-1e999"):
            variants.append(b'{"unused":' + token + b'}')
        for raw in variants:
            with self.subTest(raw=raw):
                report, patch_path = self.pair(raw)
                self.refuse(report, patch_path)

    def test_unsupported_rendering_layout_refuses(self):
        base = json.loads(self.original_report)
        variants = [("schema", "testpilot.recheck/1"), ("status", None),
                    ("test_files", []), ("changed_functions", [{}]),
                    ("rounds", "text"), ("ledger", {}), ("final", []),
                    ("coverage", "missing"), ("pytest_selection", False)]
        for key, value in variants:
            with self.subTest(field=key):
                document = copy.deepcopy(base)
                document[key] = value
                report, patch_path = self.pair(json.dumps(document).encode())
                self.refuse(report, patch_path)
        for field in ("tokens_estimated", "cost_is_complete"):
            document = copy.deepcopy(base)
            document["ledger"][field] = "false"
            report, patch_path = self.pair(json.dumps(document).encode())
            self.refuse(report, patch_path)

    def test_literal_text_and_unavailable_result_remain_native(self):
        document = json.loads(self.original_report)
        document.update(message="<script>alert('x')</script> & \ud800 \u0000", final=None,
                        coverage=None, pytest_selection={"keyword":"<img src=x>","marker":None})
        report, patch_path = self.pair(json.dumps(document).encode())
        _, data = self.receive(report, patch_path, self.root / "literal.html")
        self.assertIn(b"&lt;script&gt;", data)
        self.assertIn(b"No generated-test result was recorded", data)
        self.assertIn(b"Coverage unavailable", data)

    def test_existing_destinations_and_publication_race_preserve_bytes(self):
        report, patch_path = self.pair()
        occupied = self.root / "occupied.html"
        occupied.write_bytes(b"prior review")
        directory = self.root / "directory"
        directory.mkdir()
        choices = [occupied, directory, report, patch_path]
        if hasattr(os, "symlink"):
            dangling = self.root / "dangling.html"
            dangling.symlink_to(self.root / "missing")
            choices.append(dangling)
        for destination in choices:
            process = self.cli(report, patch_path, destination)
            self.assertEqual(process.returncode, 2)
        self.assertEqual(occupied.read_bytes(), b"prior review")
        self.assertEqual(report.read_bytes(), self.original_report)
        self.assertEqual(patch_path.read_bytes(), self.original_patch)
        target = self.root / "concurrent.html"
        def occupy(source, destination):
            Path(destination).write_bytes(b"concurrent owner")
            raise FileExistsError("name became occupied")
        with patch.object(saved_report.os, "link", side_effect=occupy):
            with self.assertRaises(FileExistsError):
                saved_report.reopen_report(report, patch_path, target)
        self.assertEqual(target.read_bytes(), b"concurrent owner")
        self.assertEqual(list(self.root.glob(".testpilot-review-*")), [])

    def test_file_limits_and_fifo_refuse_without_output(self):
        report, patch_path = self.pair()
        oversized = self.root / "oversized.json"
        with oversized.open("wb") as stream:
            stream.truncate(saved_report.MAX_REPORT_BYTES + 1)
        process = self.cli(oversized, patch_path, self.root / "large.html")
        self.assertEqual(process.returncode, 2)
        self.assertIn(b"exceeds", process.stderr)
        self.assertFalse((self.root / "large.html").exists())
        if hasattr(os, "mkfifo") and hasattr(os, "O_NONBLOCK"):
            fifo = self.root / "no-writer.fifo"
            os.mkfifo(fifo)
            for report_input, patch_input in ((fifo, patch_path), (report, fifo)):
                process = self.cli(report_input, patch_input, self.root / "fifo.html")
                self.assertEqual(process.returncode, 2)
                self.assertIn(b"regular file", process.stderr)
                self.assertFalse((self.root / "fifo.html").exists())

    def test_no_runner_or_model_and_cleanup_warning_after_publication(self):
        report, patch_path = self.pair()
        destination = self.root / "no-execution.html"
        with patch("testpilot.sandbox.run_pytest", side_effect=AssertionError("runner called")), \
             patch("testpilot.model.make_client", side_effect=AssertionError("model called")):
            saved_report.reopen_report(report, patch_path, destination)
        with patch.object(saved_report.os, "unlink", side_effect=OSError("authored cleanup refusal")):
            receipt = saved_report.reopen_report(report, patch_path, self.root / "published.html")
        self.assertIn("cleanup_warning", receipt)
        self.assertEqual((self.root / "published.html").stat().st_size, receipt["bytes"])
        for temporary in self.root.glob(".testpilot-review-*"):
            temporary.unlink()


if __name__ == "__main__":
    unittest.main()
