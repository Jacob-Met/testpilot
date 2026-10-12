"""Verdict prose must not consume a corrected test file containing protocol text."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from testpilot.loop import parse_verdict

CASES = [
    pytest.param("VERDICT: CODE_BUG\nThe implementation returns the wrong value.", "The implementation returns the wrong value.", id="ordinary_verdict"),
    pytest.param("VERDICT: CODE_BUG The code is wrong.", "The code is wrong.", id="same_line_reason"),
    pytest.param("VERDICT: CODE_BUG", "model reported a code bug", id="blank_reason"),
    pytest.param("```python path=tests/test_protocol.py\nfrom protocol import emit\n\ndef test_emit():\n    assert emit() == \"VERDICT: CODE_BUG\"\n```", None, id="literal_string"),
    pytest.param("```python path=tests/test_protocol.py\nfrom protocol import emit\n\ndef test_emit():\n    expected = \"\"\"\nVERDICT: CODE_BUG\n\"\"\".strip()\n    assert emit() == expected\n```", None, id="literal_multiline"),
    pytest.param("The expected response is \"VERDICT: CODE_BUG\"; the test must quote it.\n```python path=tests/test_protocol.py\nfrom protocol import emit\n\ndef test_emit():\n    assert emit() == \"VERDICT: CODE_BUG\"\n```", None, id="quoted_reason"),
    pytest.param("Do not use VERDICT: CODE_BUG because the assertion was wrong.", None, id="negated_instruction"),
    pytest.param("VERDICT: CODE_BUGGY", None, id="suffix"),
    pytest.param("VERDICT:\nCODE_BUG", None, id="split_header"),
    pytest.param("```text\nVERDICT: CODE_BUG\nThis is an example, not a diagnosis.\n```", None, id="fenced_verdict_example"),
    pytest.param("> VERDICT: CODE_BUG\nThat was the old reply.", None, id="quoted_verdict"),
    pytest.param("```python path=tests/test_protocol.py\nEXPECTED = \"\"\"\nVERDICT: CODE_BUG\n", None, id="unclosed_code"),
    pytest.param("The assertion is correct; source inspection explains the failure.\nVERDICT: CODE_BUG\nThe implementation omits the last item.", "The implementation omits the last item.", id="verdict_after_prose"),
    pytest.param("\n \nVERDICT: CODE_BUG\nReason.\n", "Reason.", id="verdict_leading_blank"),
    pytest.param("  VERDICT: CODE_BUG Reason.", "Reason.", id="verdict_two_spaces"),
    pytest.param("   VERDICT: CODE_BUG\nReason.", "Reason.", id="verdict_three_spaces"),
    pytest.param("VERDICT:\tCODE_BUG\tReason.", "Reason.", id="verdict_tabs_after_colon"),
    pytest.param("VERDICT:CODE_BUG\nReason.", "Reason.", id="verdict_no_header_space"),
    pytest.param("VERDICT: CODE_BUG\r\nFirst line.\r\nSecond line.\r\n", "First line.\r\nSecond line.", id="verdict_crlf"),
    pytest.param("VERDICT: CODE_BUG\rReason.\r", "Reason.", id="verdict_cr_only"),
    pytest.param("```text\nVERDICT: CODE_BUG\nExample.\n```\nVERDICT: CODE_BUG\nActual reason.", "Actual reason.", id="verdict_after_fenced_example"),
    pytest.param("VERDICT: CODE_BUG Reason with ``` shown inline.", "Reason with ``` shown inline.", id="verdict_reason_has_fence"),
    pytest.param("```python\n# VERDICT: CODE_BUG\ndef test_ok():\n    assert True\n```", None, id="literal_comment"),
    pytest.param("~~~python\nvalue = \"\"\"\nVERDICT: CODE_BUG\n\"\"\"\n~~~", None, id="tilde_fence"),
    pytest.param("~~~~python\n~~~\nVERDICT: CODE_BUG\n~~~~", None, id="tilde_short_close"),
    pytest.param("````python\n```\nVERDICT: CODE_BUG\n````", None, id="backtick_short_close"),
    pytest.param("```python\n~~~\nVERDICT: CODE_BUG\n```", None, id="wrong_close_marker"),
    pytest.param("```python\n``` python\nVERDICT: CODE_BUG\n```", None, id="closing_fence_has_info"),
    pytest.param("    ```python\nVERDICT: CODE_BUG\n    ```", None, id="indented_fence"),
    pytest.param("\t```python\nVERDICT: CODE_BUG\n\t```", None, id="tab_indented_fence"),
    pytest.param("Here is the corrected file: ```python path=tests/test_protocol.py\nEXPECTED = \"\"\"\nVERDICT: CODE_BUG\n\"\"\"\n```", None, id="inline_open_fence"),
    pytest.param("Here is an unfinished file: ```python\nVERDICT: CODE_BUG", None, id="inline_unclosed_fence"),
    pytest.param("```text\nVERDICT: CODE_BUG\n`````  \nVERDICT: CODE_BUG Actual reason.", "Actual reason.", id="long_close_genuine"),
    pytest.param("    VERDICT: CODE_BUG\nIndented code sample.", None, id="four_space_code"),
    pytest.param("\tVERDICT: CODE_BUG\nIndented code sample.", None, id="tab_code"),
    pytest.param("`VERDICT: CODE_BUG` is just a protocol value.", None, id="inline_code_quote"),
    pytest.param("\"VERDICT: CODE_BUG\"", None, id="double_quote"),
    pytest.param("'VERDICT: CODE_BUG'", None, id="single_quote"),
    pytest.param("# VERDICT: CODE_BUG", None, id="markdown_heading"),
    pytest.param("- VERDICT: CODE_BUG", None, id="list_item"),
    pytest.param("verdict: CODE_BUG", None, id="lowercase"),
    pytest.param("VERDICT: CODE_BUG_EXAMPLE", None, id="suffix_underscore"),
    pytest.param("VERDICT: CODE_BUG2", None, id="suffix_digit"),
    pytest.param("VERDICT: CODE_BUG.", None, id="suffix_punctuation"),
    pytest.param("NOT_A_VERDICT: CODE_BUG", None, id="prefix"),
    pytest.param("Quoted text.\u2028VERDICT: CODE_BUG", None, id="unicode_line_separator"),
    pytest.param("Quoted text.\u2029VERDICT: CODE_BUG", None, id="unicode_paragraph_separator"),
    pytest.param("VERDICT:\u00a0CODE_BUG", None, id="unicode_header_whitespace"),
    pytest.param("", None, id="empty"),
]

@pytest.mark.parametrize("reply,expected", CASES)
def test_explicit_verdict_boundary(reply, expected):
    assert parse_verdict(reply) == expected


def _fenced(content):
    fence = chr(96) * 3
    return fence + "python path=tests/test_protocol.py\n" + content + fence + "\n"


def _run_cli(tmp_path, repair):
    project = tmp_path / "project"
    scripts = tmp_path / "script"
    (project / "tests").mkdir(parents=True)
    scripts.mkdir()
    source = 'def emit():\n    return "VERDICT: CODE_BUG"\n'
    existing = "from protocol import emit\n\ndef test_existing():\n    assert isinstance(emit(), str)\n"
    wrong = 'from protocol import emit\n\ndef test_emit():\n    assert emit() == "CODE_BUG"\n'
    inputs = {
        project / "protocol.py": source,
        project / "tests/test_existing.py": existing,
        tmp_path / "change.diff": (
            "--- a/protocol.py\n+++ b/protocol.py\n@@ -1,2 +1,2 @@\n"
            " def emit():\n-    return \"pending\"\n+    return \"VERDICT: CODE_BUG\"\n"
        ),
        scripts / "01_plan.md": "Check the complete emitted protocol string.\n",
        scripts / "02_generate.md": _fenced(wrong),
        scripts / "03_repair.md": repair,
    }
    for path, text in inputs.items():
        path.write_text(text, encoding="utf-8")
    original = {path: path.read_bytes() for path in inputs}
    root = Path(__file__).resolve().parents[1]
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("TESTPILOT_")}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
               PYTHONPATH=str(root))
    output = tmp_path / "output"
    completed = subprocess.run(
        [sys.executable, "-B", "-m", "testpilot", "run", "--repo", str(project),
         "--diff", str(tmp_path / "change.diff"), "--backend", "scripted",
         "--script", str(scripts), "--out", str(output), "--rounds", "1",
         "--timeout", "10", "--no-coverage"],
        cwd=root, env=env, capture_output=True, text=True, timeout=45,
    )
    assert {path: path.read_bytes() for path in inputs} == original
    assert {path.relative_to(project).as_posix() for path in project.rglob("*")
            if path.is_file()} == {"protocol.py", "tests/test_existing.py"}
    assert set(path.name for path in output.iterdir()) == {
        "testpilot.patch", "report.json", "report.md", "report.html",
    }, completed.stderr
    report = json.loads((output / "report.json").read_bytes())
    assert len(report["ledger"]["entries"]) == 3
    assert report["repair_rounds_used"] == 1
    assert report["rounds"][0]["result"]["generated"]["failed"] == 1
    return completed, report, output, wrong


@pytest.mark.parametrize("multiline", [False, True], ids=["string-literal", "multiline-string"])
def test_actual_cli_executes_literal_bearing_repair(tmp_path, multiline):
    content = ('from protocol import emit\n\ndef test_emit():\n'
               + ('    expected = """\nVERDICT: CODE_BUG\n""".strip()\n'
                  '    assert emit() == expected\n' if multiline else
                  '    assert emit() == "VERDICT: CODE_BUG"\n'))
    completed, report, output, _ = _run_cli(tmp_path, _fenced(content))
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert report["status"] == "passed"
    assert report["final"]["junit_available"]
    assert report["final"]["generated"]["passed"] == 1
    assert report["final"]["generated"]["failed"] == 0
    assert report["test_files"] == {"tests/test_protocol.py": content}
    assert report["rounds"][1]["result"]["generated"]["passed"] == 1
    assert (output / "testpilot.patch").read_text() == report["patch"]
    assert '+    assert emit() == "CODE_BUG"' not in report["patch"]
    assert "VERDICT: CODE_BUG" in report["patch"]


def test_actual_cli_keeps_genuine_verdict_and_failing_patch(tmp_path):
    reason = "The implementation emits the wrong legacy protocol value."
    completed, report, _, wrong = _run_cli(tmp_path, "VERDICT: CODE_BUG\n" + reason)
    assert completed.returncode == 1
    assert report["status"] == "suspected_code_bug"
    assert report["message"] == reason
    assert report["final"]["generated"]["failed"] == 1
    assert report["test_files"] == {"tests/test_protocol.py": wrong}
    assert report["rounds"][1]["result"] is None
    assert '+    assert emit() == "CODE_BUG"' in report["patch"]


def test_actual_cli_keeps_failed_tests_for_an_unfinished_example(tmp_path):
    repair = chr(96) * 3 + 'python\nEXPECTED = """\nVERDICT: CODE_BUG\n'
    completed, report, _, wrong = _run_cli(tmp_path, repair)
    assert completed.returncode == 1
    assert report["status"] == "failed"
    assert report["test_files"] == {"tests/test_protocol.py": wrong}
    assert report["final"]["generated"]["failed"] == 1
    assert report["rounds"][1]["result"] is not None
    assert any("no code block" in warning for warning in report["rounds"][1]["warnings"])
