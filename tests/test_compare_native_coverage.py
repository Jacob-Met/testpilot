"""Receive current producer reports, including unavailable changed-line coverage."""
from __future__ import annotations

import base64
import json
import re

import pytest

from testpilot.compare import ComparisonError, parse_report
from testpilot.loop import TestPilot
from testpilot.model import ScriptedModel


@pytest.fixture
def native_report(tmp_path, request):
    pytest.importorskip("coverage")
    mode = request.param
    repo = tmp_path / "project"
    repo.mkdir()
    (repo / "tests").mkdir()
    (repo / "tests/test_existing.py").write_text(
        "import calc\n\ndef test_existing():\n    assert callable(calc.answer)\n"
    )
    source = "def answer():\n    return 7\n"
    targets = None
    if mode == "explicit_unchanged":
        source = "LIMIT = 7\n\ndef answer():\n    return LIMIT\n"
        diff = "--- a/calc.py\n+++ b/calc.py\n@@ -1 +1 @@\n-LIMIT = 6\n+LIMIT = 7\n"
        targets = ["calc.py::answer"]
    elif mode == "pure_deletion":
        diff = ("--- a/calc.py\n+++ b/calc.py\n@@ -1,3 +1,2 @@\n"
                " def answer():\n-    obsolete = 1\n     return 7\n")
    else:
        diff = ("--- a/calc.py\n+++ b/calc.py\n@@ -1,2 +1,2 @@\n"
                " def answer():\n-    return 6\n+    return 7\n")
    (repo / "calc.py").write_text(source)
    tests = ("```python path=tests/test_answer.py\nfrom calc import answer\n\n"
             "def test_answer():\n    assert answer() == 7\n```\n")
    model = ScriptedModel(["Check the recorded answer.", tests])
    result = TestPilot(model, max_repair_rounds=0, timeout_s=30,
                       coverage=mode != "no_coverage").run(repo, diff, targets=targets)
    assert result.status == "passed"
    assert len(model.calls) == 2
    assert result.final["generated"]["passed"] == 1
    assert not (repo / "tests/test_answer.py").exists()
    assert (repo / "calc.py").read_text() == source
    return result.to_dict()


@pytest.mark.parametrize("native_report", [
    "pure_deletion", "explicit_unchanged", "measured", "no_coverage"
], indirect=True)
def test_current_native_coverage_compares_without_fabricated_percentages(
    native_report, tmp_path, monkeypatch
):
    from testpilot import __main__ as cli

    def forbidden(*args, **kwargs):
        pytest.fail("comparing saved reports must not execute a test run or call a model")

    monkeypatch.setattr(cli, "make_client", forbidden)
    monkeypatch.setattr(cli.TestPilot, "run", forbidden)
    raw = json.dumps(native_report, ensure_ascii=True, indent=2).encode()
    originals = [b"\xef\xbb\xbf" + raw.replace(b"\n", b"\r\n"), raw + b"\n"]
    before, after = tmp_path / "before.json", tmp_path / "after.json"
    before.write_bytes(originals[0])
    after.write_bytes(originals[1])
    output = tmp_path / "comparison.html"
    assert cli.main(["compare", "--before", str(before), "--after", str(after),
                     "--out", str(output)]) == 0
    page = output.read_text()
    assert "None%" not in page
    downloaded = re.findall(r'href="data:application/json;base64,([^"]+)"', page)
    assert [base64.b64decode(data) for data in downloaded] == originals
    assert [before.read_bytes(), after.read_bytes()] == originals
    coverage = native_report["coverage"]
    for label, key in [("Changed lines before generation", "changed_lines_before"),
                       ("Changed lines after generation", "changed_lines_after")]:
        row = re.search(r"<tr><td>" + label + r"</td>.*?</tr>", page, re.DOTALL).group()
        expected = "Unavailable" if coverage is None or coverage[key] is None else str(coverage[key]) + "%"
        assert row.count(">" + expected + "<") == 2


@pytest.mark.parametrize("native_report", ["pure_deletion"], indirect=True)
def test_nullable_changed_line_coverage_keeps_required_fields_and_native_types(native_report):
    for key, value in [("total_before", None), ("changed_lines_before", False),
                       ("changed_lines_after", "0"), ("changed_lines_after", -1)]:
        document = json.loads(json.dumps(native_report))
        document["coverage"][key] = value
        with pytest.raises(ComparisonError):
            parse_report(json.dumps(document).encode())
    for key in ("changed_lines_before", "changed_lines_after"):
        document = json.loads(json.dumps(native_report))
        del document["coverage"][key]
        with pytest.raises(ComparisonError):
            parse_report(json.dumps(document).encode())
