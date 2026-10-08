"""Passive consumer controls and real saved-test CLI output receiving."""
import base64
import hashlib
from html.parser import HTMLParser
import json

import pytest

from testpilot.__main__ import main
from testpilot.recheck import render_recheck
from testpilot.recheck_html import render_recheck_html
from testpilot.sandbox import CaseResult, SandboxResult


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.links = []
        self.parts = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == "a":
            self.links.append(dict(attrs))

    def handle_data(self, text):
        self.parts.append(text)

    @property
    def text(self):
        return "".join(self.parts)

    def download(self):
        links = [a for a in self.links if a.get("download") == "recheck.json"]
        assert len(links) == 1
        assert links[0]["href"].startswith("data:application/json;base64,")
        return base64.b64decode(links[0]["href"].split(",", 1)[1], validate=True)


def sample():
    # Explicit consumer fixture using the native result serializer; it is not
    # a claim that these counterfactual test cases were executed.
    name = "tests/test_retained.py"
    content = "# 原文\r\nassert '</script> & <img src=x>'\n"
    final = SandboxResult(
        1, False, 0.125, 10, "output </script> & text\n",
        [CaseResult("spec.test_existing::test_ok", "passed"),
         CaseResult("tests.test_retained::test_bad[<&>]", "failed", "actual < expected & 2\r\n", name)],
        generated_files=[name], junit_available=True,
    ).to_dict()
    return {
        "schema": "testpilot.recheck/1", "status": "failed", "ok": False,
        "repo": "/authored/checkout", "python": "/authored/env/python",
        "started_at": "2026-01-01T23:59:59+00:00", "finished_at": "2026-01-02T00:00:00+00:00",
        "source_report": {"path": "/authored/original.json", "sha256": "a" * 64, "recorded_status": "passed"},
        "test_files": {name: content},
        "retained_tests": [{"path": name, "bytes": len(content.encode()), "sha256": hashlib.sha256(content.encode()).hexdigest(), "placement": "temporary"}],
        "final": final, "model_calls": 0,
        "scope": "Current selected-suite execution of exact retained tests; no new model calls or historical coverage comparison.",
    }


def encoded(data):
    return (json.dumps(data, ensure_ascii=True, indent=2) + "\n").encode()


def test_literal_case_source_identity_and_exact_download():
    data = sample()
    raw = encoded(data)
    page = Page(render_recheck_html(raw))
    assert page.download() == raw
    assert hashlib.sha256(raw).hexdigest() in page.text
    for value in [data["repo"], data["python"], data["started_at"], data["finished_at"], data["source_report"]["sha256"], "actual < expected & 2", "test_bad[<&>]", "assert '</script> & <img src=x>'"]:
        assert value in page.text
    assert "Historical source status (not this result)" in page.text
    assert "Recorded pytest output tail" in page.text
    assert "\\u000d" in page.text
    assert not any(tag in {"script", "img", "iframe", "object", "form"} for tag, _ in page.tags)
    assert all(a["href"].startswith(("#", "data:application/json;base64,")) for a in page.links)
    assert encoded(data) == raw


def test_incomplete_junit_counts_stay_unavailable_and_timeout_stays_recorded():
    data = sample()
    data["final"] = SandboxResult(None, True, 0.201, 0.2, "before timeout", generated_files=["tests/test_retained.py"]).to_dict()
    page = Page(render_recheck_html(encoded(data)))
    assert "Case counts are unavailable" in page.text
    assert "No individual case records are available" in page.text
    assert "TIMEOUT after 0.2s" in page.text
    assert "before timeout" in page.text
    assert not any(tag == "table" for tag, _ in page.tags)


def test_no_retained_pass_does_not_become_success():
    data = sample()
    name = "tests/test_retained.py"
    data["final"] = SandboxResult(0, False, .1, 2, "", [CaseResult("existing", "passed"), CaseResult("retained", "skipped", "not exercised", name)], generated_files=[name], junit_available=True).to_dict()
    data["status"] = "no_tests"
    page = Page(render_recheck_html(encoded(data)))
    assert "no_tests" in page.text
    assert "not exercised" in page.text
    assert "0 passed of 1 collected" in page.text
    assert page.download() == encoded(data)


def test_control_surrogate_and_raw_json_spelling_are_preserved_in_download():
    data = sample()
    data["final"]["output"] = "NUL:\0 CR:\r surrogate:\ud800 DEL:\x7f original:原文"
    raw = encoded(data).replace(b"\n", b"\r\n") + b" \t"
    page = Page(render_recheck_html(raw))
    for code in ("\\u0000", "\\u000d", "\\ud800", "\\u007f"):
        assert code in page.text
    assert page.download() == raw
    assert "original:原文" in page.text


@pytest.mark.parametrize("raw,error", [(b'{}', ValueError), (b'{"schema":"testpilot.recheck/9"}', ValueError), (b'not JSON', ValueError), ("not bytes", TypeError)])
def test_other_report_inputs_are_not_presented_as_native_rechecks(raw, error):
    with pytest.raises(error):
        render_recheck_html(raw)


@pytest.mark.parametrize("fixed,exit_code", [(False, 1), (True, 0)])
def test_actual_cli_writes_matching_json_and_md_plus_passive_page(tmp_path, fixed, exit_code):
    project = tmp_path / "project"
    project.mkdir()
    (project / "subject.py").write_text("def result():\n    return " + ("9" if fixed else "8") + "\n")
    retained = "from subject import result\ndef test_result():\n    assert result() == 9\n"
    saved = tmp_path / "authored-saved.json"
    saved.write_text(json.dumps({"status": "passed", "test_files": {"tests/test_retained.py": retained}}))
    original = {p: p.read_bytes() for p in [project / "subject.py", saved]}
    output = tmp_path / "out"
    assert main(["recheck", "--repo", str(project), "--report", str(saved), "--out", str(output)]) == exit_code
    raw = (output / "recheck.json").read_bytes()
    data = json.loads(raw)
    page = Page((output / "recheck.html").read_text())
    assert page.download() == raw
    assert data["model_calls"] == 0
    assert data["status"] == ("passed" if fixed else "failed")
    assert data["source_report"]["recorded_status"] == "passed"
    # Compare the exact pre-existing serialization contract, including the
    # platform's native text newlines, using independent reference files.
    reference_json = tmp_path / "reference.json"
    reference_md = tmp_path / "reference.md"
    reference_json.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    reference_md.write_text(render_recheck(data), encoding="utf-8")
    assert raw == reference_json.read_bytes()
    assert (output / "recheck.md").read_bytes() == reference_md.read_bytes()
    assert {p: p.read_bytes() for p in original} == original
    assert not (project / "tests").exists()
    assert sorted(p.name for p in output.iterdir()) == ["recheck.html", "recheck.json", "recheck.md"]


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX authored file-size limit")
def test_actual_html_write_failure_is_delivery_failure_not_test_success(tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import sys

    project = tmp_path / "project"
    project.mkdir()
    saved = tmp_path / "saved.json"
    saved.write_text(json.dumps({"test_files": {"tests/test_retained.py": "def test_ok():\n    assert True\n"}}))
    out = tmp_path / "out"
    # Bound this owned child only. Native JSON/Markdown fit; the newly rendered
    # page exceeds the limit, exercising a real writer failure after pytest.
    command = (
        "import resource,signal;"
        "resource.setrlimit(resource.RLIMIT_FSIZE,(8192,8192));"
        "signal.signal(signal.SIGXFSZ,signal.SIG_IGN);"
        "from testpilot.__main__ import main;"
        "raise SystemExit(main())"
    )
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    result = subprocess.run([sys.executable, "-c", command, "recheck", "--repo", str(project), "--report", str(saved), "--out", str(out)], env=env, capture_output=True, timeout=20)
    assert result.returncode == 2
    assert b"cannot recheck saved tests" in result.stderr
    assert result.stdout == b""
    assert json.loads((out / "recheck.json").read_text())["ok"] is True
    assert (out / "recheck.html").stat().st_size == 8192
    assert not (out / "recheck.html").read_bytes().endswith(b"</html>\n")
