"""Exact passive per-side generated-source downloads from saved comparisons."""
from __future__ import annotations

import base64
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from testpilot.compare import parse_report
from testpilot.compare_html import render_comparison


def document(files):
    return {"status": "no_tests", "changed_functions": [], "test_files": files,
            "tests_written": 0, "repair_rounds_used": 0, "max_repair_rounds": 0,
            "final": None, "coverage": None, "rounds": [], "plan": "", "message": "",
            "patch": "", "ledger": {"total_tokens": 0, "total_cost_usd": 0,
            "cost_is_complete": False, "tokens_estimated": False,
            "by_model": {}, "entries": []}, "extra": {"literal": "0009 <inert>"}}


def saved(files, bom=False):
    raw = json.dumps(document(files), ensure_ascii=True, indent=2).encode()
    if bom:
        raw = b"\xef\xbb\xbf" + raw.replace(b"\n", b"\r\n")
    return parse_report(raw, "same <label>.json")


class Elements(HTMLParser):
    def __init__(self, page):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.notes = []
        self.details = {}
        self.tags = []
        self.active = None
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if tag == "a":
            self.active = {"tag": tag, **attrs, "text": ""}
            self.links.append(self.active)
        elif tag == "p" and "generated-source-unavailable" in attrs.get("class", "").split():
            self.active = {"tag": tag, **attrs, "text": ""}
            self.notes.append(self.active)
        if tag == "details" and "id" in attrs:
            self.details[attrs["id"]] = "open" in attrs

    def handle_data(self, text):
        if self.active is not None:
            self.active["text"] += text

    def handle_endtag(self, tag):
        if self.active is not None and self.active["tag"] == tag:
            self.active = None

    def source_links(self):
        return [x for x in self.links if "generated-source-download" in x.get("class", "").split()]


def payload(link):
    head, data = link["href"].split(",", 1)
    if head != "data:text/plain;charset=utf-8;base64":
        raise AssertionError("Expected a passive UTF-8 source data URL")
    return base64.b64decode(data, validate=True)


class GeneratedDownloads(unittest.TestCase):
    def test_fixed_roles_and_existing_file_order_keep_each_source(self):
        before = {"z.py": "old\r\n", "a.py": "", "removed.py": "removed"}
        after = {"z.py": "new\n", "a.py": "", "added.py": "added"}
        found = Elements(render_comparison(saved(before), saved(after)))
        expected = [(0, "before", b""), (0, "after", b""), (1, "after", b"added"),
                    (2, "before", b"removed"), (3, "before", b"old\r\n"), (3, "after", b"new\n")]
        links = found.source_links()
        self.assertEqual(len(links), len(expected))
        for link, (index, role, raw) in zip(links, expected):
            self.assertEqual((link["data-file-index"], link["data-role"]), (str(index), role))
            self.assertEqual(link["download"], f"testpilot-{role}-file-{index}.txt")
            self.assertEqual(link["text"], f"Download {role.title()} source")
            self.assertEqual(payload(link), raw)
        self.assertEqual(found.details, {"file-0": False, "file-1": True, "file-2": True, "file-3": True})

    def test_complete_literal_utf8_including_recorded_feff_and_long_source(self):
        text = "\ufeff  \n\r\n\tΩ中😀\0\x1b <inert>\r" + "x" * 200_001 + "  "
        found = Elements(render_comparison(saved({"long.py": text}), saved({"long.py": "after"})))
        links = found.source_links()
        self.assertEqual(len(links), 2)
        self.assertEqual(payload(links[0]), text.encode("utf-8"))
        self.assertTrue(payload(links[0]).startswith(b"\xef\xbb\xbf"))
        self.assertEqual(payload(links[1]), b"after")
        self.assertNotIn("inert", found.tags)

    def test_unpaired_surrogate_is_local_to_its_side(self):
        before = saved({"a.py": "left\ud800", "b.py": "valid Ω"})
        after = saved({"a.py": "valid 😀", "b.py": "right\udfff"})
        page = render_comparison(before, after)
        found = Elements(page)
        self.assertEqual([(x["data-file-index"], x["data-role"], payload(x)) for x in found.source_links()],
                         [("0", "after", "valid 😀".encode()), ("1", "before", "valid Ω".encode())])
        self.assertEqual([(x["data-file-index"], x["data-role"]) for x in found.notes],
                         [("0", "before"), ("1", "after")])
        self.assertTrue(all("unavailable" in x["text"] and "unpaired surrogate" in x["text"] for x in found.notes))
        self.assertIn("\\ud800", page)
        self.assertIn("\\udfff", page)

    def test_recorded_paths_cannot_select_a_filename_or_create_markup(self):
        path = '../same/<img src="https://invalid.example/"> & Ω.py'
        found = Elements(render_comparison(saved({path: "one"}), saved({path: "two"})))
        self.assertEqual([x["download"] for x in found.source_links()],
                         ["testpilot-before-file-0.txt", "testpilot-after-file-0.txt"])
        self.assertNotIn("img", found.tags)
        self.assertNotIn("script", found.tags)

    def test_original_json_and_script_free_contract_remain_exact(self):
        before, after = saved({"a.py": "old\r\n"}, True), saved({"a.py": "new\n"})
        page = render_comparison(before, after)
        found = Elements(page)
        original = [x for x in found.links if x.get("id") in ("download-before", "download-after")]
        self.assertEqual([base64.b64decode(x["href"].split(",", 1)[1]) for x in original], [before.raw, after.raw])
        self.assertEqual([x["download"] for x in original], ["before-report.json", "after-report.json"])
        self.assertIn("default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'", page)
        self.assertNotIn("script", found.tags)

    def test_empty_maps_do_not_add_controls_or_change_absence(self):
        page = render_comparison(saved({}), saved({}))
        found = Elements(page)
        self.assertEqual(found.source_links(), [])
        self.assertEqual(found.notes, [])
        self.assertIn("Neither report retained generated files.", page)

    def test_ordinary_cli_saves_source_links_without_executing_text(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            before, after, output = root / "before.json", root / "after.json", root / "comparison.html"
            before.write_bytes(saved({"test_saved.py": "raise RuntimeError('data only')\r\n"}).raw)
            after.write_bytes(saved({"test_saved.py": ""}).raw)
            inputs = [before.read_bytes(), after.read_bytes()]
            args = [sys.executable, "-B", "-m", "testpilot", "compare", "--before", str(before),
                    "--after", str(after), "--out", str(output)]
            child = subprocess.run(args, cwd=project, capture_output=True, timeout=20)
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertEqual(child.stderr, b"")
            links = Elements(output.read_text()).source_links()
            self.assertEqual([payload(x) for x in links], [b"raise RuntimeError('data only')\r\n", b""])
            self.assertEqual([before.read_bytes(), after.read_bytes()], inputs)


if __name__ == "__main__":
    unittest.main()
