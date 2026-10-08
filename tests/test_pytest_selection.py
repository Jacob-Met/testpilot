"""Native generation consumers for keyword/marker scope; no mocked pytest runner."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

import testpilot
from testpilot.loop import TestPilot, write_outputs
from testpilot.model import ScriptedModel

PACKAGE_ROOT = Path(testpilot.__file__).resolve().parent.parent
DIFF = "--- a/answer.py\n+++ b/answer.py\n@@ -1,2 +1,2 @@\n def answer():\n-    return 1\n+    return 2\n"


def snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


@pytest.fixture
def project(tmp_path):
    repo = tmp_path / "project"
    (repo / "tests").mkdir(parents=True)
    (repo / "answer.py").write_text("def answer():\n    return 2\n", encoding="utf-8")
    (repo / "pytest.ini").write_text(
        "[pytest]\nmarkers =\n    unit: local fixture tests\n    external: deliberately failing fixture\n",
        encoding="utf-8",
    )
    (repo / "tests/test_existing.py").write_text(
        "import pytest\nfrom answer import answer\n\n"
        "@pytest.mark.unit\ndef test_focus_existing():\n    assert answer() == 2\n\n"
        "@pytest.mark.external\ndef test_remote_existing():\n    assert False, 'offline external stand-in'\n",
        encoding="utf-8",
    )
    return repo


def generated(*, name="test_focus_generated", expected=2, marked=True):
    return ("import pytest\nfrom answer import answer\n\n"
            + ("@pytest.mark.unit\n" if marked else "")
            + f"def {name}():\n    assert answer() == {expected}\n")


def fenced(content):
    return "```python path=tests/test_generated.py\n" + content + "```\n"


def pilot_run(repo, responses, **kwargs):
    model = ScriptedModel(responses)
    result = TestPilot(model, coverage=False, python=sys.executable, timeout_s=15,
                       max_repair_rounds=kwargs.pop("max_repair_rounds", 0), **kwargs).run(repo, DIFF)
    return result, model


def cli(repo, tmp_path, *selectors):
    script = tmp_path / "responses"
    script.mkdir()
    (script / "01.txt").write_text("Check the answer using local unit cases.")
    (script / "02.txt").write_text(fenced(generated()))
    diff = tmp_path / "change.diff"
    diff.write_text(DIFF)
    out = tmp_path / "output"
    env = {**os.environ, "PYTHONPATH": str(PACKAGE_ROOT), "PYTHONDONTWRITEBYTECODE": "1"}
    run = subprocess.run([
        sys.executable, "-B", "-m", "testpilot", "run", "--repo", str(repo),
        "--diff", str(diff), "--backend", "scripted", "--script", str(script),
        "--rounds", "0", "--timeout", "15", "--python", sys.executable,
        "--no-coverage", "--out", str(out), *selectors,
    ], env=env, capture_output=True, text=True, timeout=45)
    return run, out


def test_cli_marker_selects_real_cases_and_preserves_exact_downloads(project, tmp_path):
    before = snapshot(project)
    run, out = cli(project, tmp_path, "--pytest-m", " unit ")
    assert run.returncode == 0, run.stdout + run.stderr
    raw = (out / "report.json").read_bytes()
    data = json.loads(raw)
    assert data["pytest_selection"] == {"keyword": None, "marker": " unit "}
    assert data["status"] == "passed"
    assert data["final"]["passed"] == 2
    assert data["final"]["generated"]["passed"] == 1
    assert data["coverage"] is None
    page = (out / "report.html").read_text()
    markdown = (out / "report.md").read_text()
    assert "Unselected tests were not verified" in page and "Unselected tests were not verified" in markdown
    assert '"marker": " unit "' in markdown
    json_data = re.search(r'data:application/json;base64,([^"\s]+)', page).group(1)
    patch_data = re.search(r'data:text/plain;charset=utf-8;base64,([^"\s]+)', page).group(1)
    assert base64.b64decode(json_data) == raw
    assert base64.b64decode(patch_data) == (out / "testpilot.patch").read_bytes()
    assert snapshot(project) == before


def test_native_keyword_and_marker_intersection(project, tmp_path):
    (project / "tests/test_intersection.py").write_text(
        "import pytest\n\n@pytest.mark.unit\ndef test_other():\n    assert False\n\n"
        "@pytest.mark.external\ndef test_focus_external():\n    assert False\n"
    )
    run, out = cli(project, tmp_path, "--pytest-k", "focus", "--pytest-m", "unit")
    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads((out / "report.json").read_text())
    assert result["final"]["passed"] == 2
    assert result["final"]["generated"]["passed"] == 1
    assert result["pytest_selection"] == {"keyword": "focus", "marker": "unit"}


def test_repair_uses_identical_selection_and_informs_each_model(project):
    before = snapshot(project)
    literal = " focus and not remote "
    result, model = pilot_run(project, ["Plan", fenced(generated(expected=9)), fenced(generated())],
                              pytest_k=literal, pytest_m="unit", max_repair_rounds=1)
    assert result.status == "passed"
    assert result.repair_rounds_used == 1
    assert result.rounds[0].result["failed"] == 1
    assert result.rounds[1].result["passed"] == 2
    assert result.rounds[1].result["generated"]["passed"] == 1
    assert len(model.calls) == 3
    for _, messages in model.calls:
        assert json.dumps({"keyword": literal, "marker": "unit"}) in messages[-1]["content"]
        assert "unselected tests are not verified" in messages[-1]["content"]
    assert snapshot(project) == before


@pytest.mark.parametrize("keyword,marker,expected_passes", [
    ("existing", "unit", 1), ("nothing_matches", None, 0),
])
def test_selected_existing_or_no_cases_cannot_qualify_patch(project, keyword, marker, expected_passes):
    result, _ = pilot_run(project, ["Plan", fenced(generated())], pytest_k=keyword, pytest_m=marker)
    assert result.status == "no_tests"
    assert not result.ok
    assert result.final["passed"] == expected_passes
    assert result.final["generated"]["passed"] == 0
    assert result.tests_written == 0
    assert result.patch and result.test_files


def test_invalid_native_expression_refuses_before_model_use(project):
    result, model = pilot_run(project, [], pytest_k="focus and (")
    assert result.status == "failed"
    assert result.final["returncode"] == 4
    assert not result.patch and not result.test_files and not model.calls
    assert result.pytest_selection == {"keyword": "focus and (", "marker": None}


def test_default_still_executes_failing_authored_case_and_omits_context(project):
    result, _ = pilot_run(project, ["Plan", fenced(generated())])
    assert result.status == "failed"
    assert result.final["failed"] == 1
    assert "pytest_selection" not in result.to_dict()


def test_empty_expression_is_literal_and_does_not_hide_failures(project):
    result, _ = pilot_run(project, ["Plan", fenced(generated())], pytest_k="", pytest_m="")
    assert result.status == "failed"
    assert result.final["failed"] == 1
    assert result.pytest_selection == {"keyword": "", "marker": ""}


@pytest.mark.parametrize("name,value", [("pytest_k", 1), ("pytest_m", True),
                                          ("pytest_k", []), ("pytest_m", "a\x00b")])
def test_api_refuses_non_literal_configuration(name, value):
    with pytest.raises(ValueError):
        TestPilot(ScriptedModel([]), **{name: value})


def test_report_escapes_literal_markup_and_option_looking_expression(project, tmp_path):
    literal = "--junitxml=<script>ignored</script>"
    result, model = pilot_run(project, [], pytest_k=literal)
    assert result.status == "failed" and result.final["returncode"] == 4
    assert not model.calls
    paths = write_outputs(result, tmp_path / "literal-output")
    page = paths["html"].read_text()
    assert "<script>ignored</script>" not in page
    assert "&lt;script&gt;ignored&lt;/script&gt;" in page
    assert json.loads(paths["json"].read_bytes())["pytest_selection"]["keyword"] == literal
