"""Public saved-comparison reading states; no generated tests or provider calls."""
from __future__ import annotations

import base64
import json
import re
from html.parser import HTMLParser

import pytest

from testpilot.compare import parse_report
from testpilot.compare_html import render_comparison


def saved(outcomes, junit=True):
    cases = [{"nodeid": "same::case", "outcome": outcome,
              "message": "" if i == 1 else "Literal <note> & Unicode Ω\ncase " + str(i)}
             for i, outcome in enumerate(outcomes)]
    final = {
        "returncode": 1, "timed_out": False, "duration_s": 0.1, "timeout_s": 10,
        "output": "retained output", "cases": cases, "coverage": None,
        "passed": outcomes.count("passed"), "failed": outcomes.count("failed"),
        "errors": outcomes.count("error"), "skipped": outcomes.count("skipped"),
        "ok": False, "summary": "Fictional recorded mixed outcomes",
    }
    if junit is not None:
        final["junit_available"] = junit
    data = {
        "status": "failed", "changed_functions": [], "test_files": {},
        "tests_written": 0, "repair_rounds_used": 0, "max_repair_rounds": 0,
        "final": final, "coverage": None, "rounds": [], "plan": "", "message": "",
        "patch": "", "ledger": {"total_tokens": 0, "total_cost_usd": 0,
        "cost_is_complete": False, "tokens_estimated": False,
        "by_model": {}, "entries": []},
        "extra": {"literal": "preserve extra data"},
    }
    raw = b"\xef\xbb\xbf" + json.dumps(data, ensure_ascii=False, indent=2).replace("\n", "\r\n").encode("utf-8")
    return parse_report(raw, "same report.json")


class Diagnostics(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_section = False
        self.heading = None
        self.role = None
        self.rows = {"Before": [], "After": []}
        self.active = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "section":
            self.in_section = attrs.get("id") == "diagnostics"
        if not self.in_section:
            return
        if tag == "h3":
            self.heading = ""
        if tag == "details":
            self.active = {"open": "open" in attrs, "text": ""}
            self.rows[self.role].append(self.active)

    def handle_data(self, data):
        if not self.in_section:
            return
        if self.heading is not None:
            self.heading += data
        if self.active is not None:
            self.active["text"] += data

    def handle_endtag(self, tag):
        if tag == "h3" and self.in_section:
            self.role, self.heading = self.heading, None
        elif tag == "details":
            self.active = None
        elif tag == "section":
            self.in_section = False


def parse_diagnostics(page):
    parsed = Diagnostics()
    parsed.feed(page)
    return parsed.rows


def test_mixed_occurrences_show_failures_in_both_columns_without_changing_payloads():
    before = saved(["passed", "failed", "skipped", "error"])
    after = saved(["error", "skipped", "failed", "passed"])
    page = render_comparison(before, after)
    rows = parse_diagnostics(page)
    assert [r["open"] for r in rows["Before"]] == [False, True, False, True, False]
    assert [r["open"] for r in rows["After"]] == [True, False, True, False, False]
    for role in ("Before", "After"):
        assert all("same::case" in r["text"] for r in rows[role][:4])
        assert "No diagnostic text recorded." in rows[role][1]["text"]
        assert "Literal <note> & Unicode Ω" in rows[role][0]["text"]
    downloads = re.findall(r'href="data:application/json;base64,([^"]+)"', page)
    assert [base64.b64decode(value) for value in downloads] == [before.raw, after.raw]
    assert "<script" not in page and "<note>" not in page
    assert "default-src 'none'" in page and "form-action 'none'" in page


@pytest.mark.parametrize("junit", [False, None])
def test_open_diagnostics_do_not_promote_incomplete_execution_evidence(junit):
    report = saved(["failed", "error"], junit)
    page = render_comparison(report, report)
    rows = parse_diagnostics(page)
    assert [r["open"] for r in rows["Before"]] == [True, True, False]
    assert [r["open"] for r in rows["After"]] == [True, True, False]
    assert page.count("Unavailable as complete execution evidence") == 4
    assert ("Availability was not recorded" if junit is None else "Unavailable") in page


@pytest.mark.parametrize("final", [None, "empty"])
def test_absent_or_empty_final_cases_do_not_add_diagnostic_disclosures(final):
    original = saved([])
    data = json.loads(original.raw.decode("utf-8-sig"))
    if final is None:
        data["final"] = None
    report = parse_report(json.dumps(data).encode("utf-8"))
    rows = parse_diagnostics(render_comparison(report, report))
    assert len(rows["Before"]) == (0 if final is None else 1)
    assert len(rows["After"]) == (0 if final is None else 1)
    assert not any(row["open"] for values in rows.values() for row in values)
