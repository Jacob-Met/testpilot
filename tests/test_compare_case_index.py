"""Native occurrence links in saved comparisons; no report-listed code execution."""
from __future__ import annotations

import base64
import json
import re
from html.parser import HTMLParser

import pytest

from testpilot.compare import parse_report
from testpilot.compare_html import render_comparison
from test_compare_diagnostics import saved, parse_diagnostics


class Index(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inside = False
        self.active = None
        self.links = []
        self.ids = []
        self.details = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "nav":
            self.inside = attrs.get("aria-label") == "Recorded failed and error cases"
        if self.inside and tag == "a":
            self.active = {"href": attrs.get("href"), "text": ""}
            self.links.append(self.active)
        if tag == "details" and "id" in attrs:
            self.details[attrs["id"]] = "open" in attrs

    def handle_data(self, value):
        if self.active is not None:
            self.active["text"] += value

    def handle_endtag(self, tag):
        if tag == "a":
            self.active = None
        if tag == "nav":
            self.inside = False


def index(page):
    result = Index()
    result.feed(page)
    return result


def test_links_keep_report_roles_and_original_duplicate_occurrence_positions():
    before = saved(["passed", "failed", "error", "failed", "skipped"])
    after = saved(["failed", "passed", "error"])
    page = render_comparison(before, after)
    found = index(page)
    expected = [
        ("before", "Before", 2, "failed"), ("before", "Before", 3, "error"),
        ("before", "Before", 4, "failed"), ("after", "After", 1, "failed"),
        ("after", "After", 3, "error"),
    ]
    assert found.links == [
        {"href": f"#diagnostic-{key}-case-{position}",
         "text": f"{role} case {position} · {outcome} · same::case"}
        for key, role, position, outcome in expected
    ]
    assert len(found.ids) == len(set(found.ids))
    for link in found.links:
        assert found.details[link["href"][1:]] is True
    states = parse_diagnostics(page)
    assert [row["open"] for row in states["Before"]] == [False, True, True, True, False, False]
    assert [row["open"] for row in states["After"]] == [True, False, True, False]


def test_literal_labels_cannot_create_targets_or_markup_and_downloads_keep_bytes():
    original = saved(["error"])
    data = json.loads(original.raw.decode("utf-8-sig"))
    label = 'same <node id="diagnostic-after-case-1"> & Ω'
    data["final"]["cases"][0]["nodeid"] = label
    raw = b"\xef\xbb\xbf" + json.dumps(data, ensure_ascii=False, indent=2).replace("\n", "\r\n").encode()
    before = parse_report(raw)
    after = saved(["passed", "failed"])
    page = render_comparison(before, after)
    found = index(page)
    assert found.links == [
        {"href": "#diagnostic-before-case-1", "text": "Before case 1 · error · " + label},
        {"href": "#diagnostic-after-case-2", "text": "After case 2 · failed · same::case"},
    ]
    assert "<node" not in page and "<script" not in page
    assert len(found.ids) == len(set(found.ids))
    encoded = re.findall(r'href="data:application/json;base64,([^"]+)"', page)
    assert [base64.b64decode(item) for item in encoded] == [before.raw, after.raw]
    assert before.raw == raw
    assert "default-src 'none'" in page and "form-action 'none'" in page


@pytest.mark.parametrize("junit", [False, None])
def test_incomplete_junit_retains_case_links_without_promoting_counts(junit):
    report = saved(["failed", "error"], junit)
    page = render_comparison(report, report)
    assert len(index(page).links) == 4
    assert page.count("Unavailable as complete execution evidence") == 4
    assert ("Availability was not recorded" if junit is None else "Unavailable") in page


@pytest.mark.parametrize("state", ["absent", "empty", "ordinary"])
def test_no_index_when_no_recorded_failure_or_error_exists(state):
    before = saved(["passed", "skipped"] if state == "ordinary" else [])
    if state == "absent":
        data = json.loads(before.raw.decode("utf-8-sig"))
        data["final"] = None
        before = parse_report(json.dumps(data).encode())
    after = saved([])
    page = render_comparison(before, after)
    assert index(page).links == []
    assert 'aria-label="Recorded failed and error cases"' not in page
    if state == "absent":
        assert "No final test result is recorded." in page
    else:
        assert "No individual test cases are recorded." in page
    assert not any(row["open"] for rows in parse_diagnostics(page).values() for row in rows)
