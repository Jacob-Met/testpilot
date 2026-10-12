"""Changed-input contracts for the saved-report consumer; no model or test execution."""
from __future__ import annotations

import base64
import copy
import json
import os
import re
from decimal import Decimal
from pathlib import Path

import pytest

from testpilot.compare import (ComparisonError, MAX_REPORT_BYTES, context_relation,
                               file_changes, parse_report, read_report, target_groups,
                               write_comparison)
from testpilot.compare_html import render_comparison, source_diff


def sample():
    return {
        "status": "passed", "changed_functions": [
            {"path": "calc.py", "qualname": "clamp", "module": "calc", "lineno": 1,
             "end_lineno": 2, "changed_lines": [2], "source": "def clamp(x):\n    return x",
             "is_method": False}],
        "repair_rounds_used": 0, "max_repair_rounds": 1, "tests_written": 1,
        "test_files": {"tests/test_calc.py": "def test_saved():\n    assert True\n"},
        "final": {
            "returncode": 0, "timed_out": False, "duration_s": 0.125, "timeout_s": 15.0,
            "output": "one recorded case\n", "cases": [
                {"nodeid": "tests.test_calc::test_saved", "outcome": "passed", "message": "",
                 "generated_file": "tests/test_calc.py"}],
            "coverage": None, "generated_files": ["tests/test_calc.py"], "junit_available": True,
            "passed": 1, "failed": 0, "errors": 0, "skipped": 0, "ok": True,
            "summary": "1 passed (recorded)",
            "generated": {"collected": 1, "passed": 1, "failed": 0, "error": 0, "skipped": 0}},
        "patch": "a saved additions-only patch\n", "coverage": None,
        "ledger": {"total_tokens": 5, "total_cost_usd": 0.0, "cost_is_complete": False,
                   "tokens_estimated": True, "by_model": {},
                   "entries": []},
        "rounds": [], "plan": "Keep the saved assertions.", "message": "", "ok": True,
    }


def raw(data=None):
    return json.dumps(sample() if data is None else data, ensure_ascii=True, indent=2).encode()


def reports(tmp_path):
    before, after = tmp_path / "before.json", tmp_path / "after.json"
    before.write_bytes(raw())
    data = sample()
    data["test_files"]["tests/test_calc.py"] += "# changed explanation\n"
    after.write_bytes(raw(data))
    return before, after


def test_exact_download_bytes_and_detached_immutable_data():
    document = sample()
    document["extra"] = {"literal": "</script><img src=x onerror=alert(1)> & \u2028 \ud800"}
    original = b"\xef\xbb\xbf" + raw(document).replace(b"\n", b"\r\n")
    saved = parse_report(original, 'same"name.json')
    with pytest.raises(TypeError):
        saved.data["test_files"]["tests/test_calc.py"] = "changed"
    with pytest.raises(TypeError):
        saved.data["extra"]["literal"] = "changed"
    page = render_comparison(saved, saved)
    encoded = re.findall(r'href="data:application/json;base64,([^"]+)"', page)
    assert len(encoded) == 2
    assert [base64.b64decode(x) for x in encoded] == [original, original]
    assert "<script" not in page and "<img" not in page
    assert saved.raw == original


def test_context_never_pairs_duplicate_labels_or_treats_a_rename_as_identity():
    before = parse_report(raw())
    data = sample()
    assert context_relation(before, before) == "Same reported target records"
    data["changed_functions"][0]["source"] = "def clamp(x):\n    return 0"
    assert context_relation(before, parse_report(raw(data))) == "Matching target labels; selected source differs"
    data = sample()
    data["changed_functions"][0]["lineno"] = 3
    data["changed_functions"][0]["end_lineno"] = 4
    assert context_relation(before, parse_report(raw(data))) == "Same selected source; selection metadata differs"
    data = sample()
    data["changed_functions"].append(copy.deepcopy(data["changed_functions"][0]))
    after = parse_report(raw(data))
    assert context_relation(before, after).startswith("Repeated target labels")
    assert len(target_groups(before, after)[0]["after"]) == 2
    data = sample()
    data["changed_functions"][0]["path"] = "moved/calc.py"
    assert context_relation(before, parse_report(raw(data))) == "Different selected targets"


def test_added_empty_and_renamed_generated_files_remain_distinct():
    data = sample()
    original_text = data["test_files"].pop("tests/test_calc.py")
    data["test_files"]["tests/test_renamed.py"] = original_text
    data["test_files"]["tests/test_empty.py"] = ""
    changes = file_changes(parse_report(raw()), parse_report(raw(data)))
    assert {x["path"]: x["status"] for x in changes} == {
        "tests/test_calc.py": "removed", "tests/test_empty.py": "added",
        "tests/test_renamed.py": "added"}
    assert next(x for x in changes if "empty" in x["path"])["after"] == ""


def test_source_diff_preserves_physical_lines_cr_and_missing_final_newline():
    delta = source_diff("a\u2028b\n", "a\u2028c\n", "test_literal.py")
    assert "@@ -1 +1 @@" in delta
    assert "-a\u2028b\n+a\u2028c\n" in delta
    assert "-a\r\n+a\n" in source_diff("a\r\n", "a\n", "test_cr.py")
    delta = source_diff("before", "after", "test_tail.py")
    assert delta.count("\\ No newline at end of file\n") == 2
    assert source_diff("x" * 200_001, "", "large.py") is None


def test_unknown_junit_does_not_promote_authored_counts_or_incomplete_cost():
    data = sample()
    data["tests_written"] = 999
    data["final"].pop("junit_available")
    data["final"].pop("generated")
    data["ledger"]["total_cost_usd"] = 0.0
    page = render_comparison(parse_report(raw(data)), parse_report(raw(data)))
    assert "Availability was not recorded" in page
    assert page.count("Unavailable as complete execution evidence") == 4
    assert "Unpriced / incomplete" in page
    assert "Tests written (reported)" in page and ">999<" in page
    data["final"]["junit_available"] = False
    page = render_comparison(parse_report(raw(data)), parse_report(raw()))
    assert "Unavailable as complete execution evidence" in page


def test_lexical_decimal_amounts_are_preserved_without_float_underflow():
    encoded = raw().replace(b'"total_cost_usd": 0.0', b'"total_cost_usd": 1e-999')
    encoded = encoded.replace(b'"cost_is_complete": false', b'"cost_is_complete": true')
    saved = parse_report(encoded)
    assert saved.data["ledger"]["total_cost_usd"] == Decimal("1e-999")
    assert "USD 1E-999" in render_comparison(saved, saved)


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(status=[]),
    lambda d: d.update(tests_written=True),
    lambda d: d.update(tests_written=-1),
    lambda d: d.update(tests_written=2**53),
    lambda d: d.pop("final"),
    lambda d: d["final"].update(junit_available="false"),
    lambda d: d["final"].update(duration_s=-1),
    lambda d: d["final"].update(generated={"collected": 1}),
    lambda d: d["ledger"].update(cost_is_complete=1),
    lambda d: d.update(test_files={"tests/test_one.py": []}),
    lambda d: d["changed_functions"][0].update(lineno=0),
    lambda d: d["changed_functions"][0].update(end_lineno=0),
    lambda d: d.update(rounds=[{"round": 0, "kind": "generate", "files": [], "warnings": []}]),
    lambda d: d.update(coverage={"total_before": 101}),
])
def test_malformed_consumed_fields_refuse(mutate):
    data = sample()
    mutate(data)
    with pytest.raises(ComparisonError):
        parse_report(raw(data))


@pytest.mark.parametrize("encoded", [
    b'{"status":"passed","status":"failed"}',
    b'{"extra":NaN}', b'{"extra":Infinity}', b'{"extra":1e999}',
    b"\xff", b"[]", b"[" * 100 + b"]" * 100,
    b" " * (MAX_REPORT_BYTES + 1),
])
def test_malformed_or_unbounded_documents_refuse(encoded):
    with pytest.raises(ComparisonError):
        parse_report(encoded)


@pytest.mark.parametrize("destination", ["before", "after", "existing", "hardlink", "symlink"])
def test_output_never_replaces_existing_or_input_alias_bytes(tmp_path, destination):
    before, after = reports(tmp_path)
    output = tmp_path / "result.html"
    if destination == "before":
        output = before
    elif destination == "after":
        output = after
    elif destination == "existing":
        output.write_bytes(b"keep existing comparison")
    elif destination == "hardlink":
        os.link(before, output)
    else:
        output.symlink_to(after)
    snapshot = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises((ComparisonError, OSError)):
        write_comparison(before, after, output)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == snapshot


@pytest.mark.parametrize("boundary", ["fsync", "link"])
def test_failed_output_staging_publishes_nothing_and_leaves_no_temp_file(tmp_path, monkeypatch, boundary):
    before, after = reports(tmp_path)
    originals = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    def fail(*args, **kwargs):
        raise OSError("independent output failure")
    monkeypatch.setattr("testpilot.compare.os." + boundary, fail)
    with pytest.raises(OSError, match="independent output failure"):
        write_comparison(before, after, tmp_path / "comparison.html")
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == originals


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO input is a native POSIX control")
def test_special_file_refuses_without_waiting_for_a_writer(tmp_path):
    pipe = tmp_path / "blocked.json"
    os.mkfifo(pipe)
    with pytest.raises(ComparisonError, match="regular"):
        read_report(pipe)
