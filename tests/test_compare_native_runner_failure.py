"""Compare actual incomplete baseline results without inventing execution counts."""
from __future__ import annotations

import base64
from html import escape
import json
import os
import re
import sys
import venv

import pytest

from testpilot.compare import ComparisonError, parse_report
from testpilot.loop import TestPilot
from testpilot.model import ScriptedModel


@pytest.mark.parametrize("failure", ["timeout", "missing_pytest"])
def test_native_runner_failure_remains_reviewable(failure, tmp_path, monkeypatch):
    repo = tmp_path / "project"
    repo.mkdir()
    source = "def answer():\n    return 7\n"
    (repo / "calc.py").write_text(source)
    diff = ("--- a/calc.py\n+++ b/calc.py\n@@ -1,2 +1,2 @@\n"
            " def answer():\n-    return 6\n+    return 7\n")
    python = sys.executable
    marker = tmp_path / "collection-started.txt"
    if failure == "timeout":
        # A real pytest collection process reaches this marker before it blocks.
        (repo / "conftest.py").write_text(
            "from pathlib import Path\nimport time\n"
            f"Path({str(marker)!r}).write_text('started')\n"
            "time.sleep(30)\n"
        )
    else:
        env_root = tmp_path / "without-pytest"
        venv.EnvBuilder(with_pip=False, system_site_packages=False,
                        symlinks=os.name != "nt").create(env_root)
        python = str(env_root / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))

    model = ScriptedModel([])
    result = TestPilot(model, max_repair_rounds=0, timeout_s=2, coverage=False,
                       python=python).run(repo, diff)
    report = result.to_dict()
    assert result.status == "failed"
    assert "complete test report" in result.message
    assert model.calls == []
    assert result.ledger["entries"] == []
    assert result.test_files == {} and result.patch == ""
    assert report["final"]["junit_available"] is False
    assert report["coverage"] is None
    assert (repo / "calc.py").read_text() == source
    if failure == "timeout":
        assert marker.read_text() == "started"
        assert report["final"]["timed_out"] is True
        assert report["final"]["returncode"] is None
        assert report["final"]["summary"] == "TIMEOUT after 2s"
    else:
        assert report["final"]["timed_out"] is False
        assert report["final"]["returncode"] == 1
        assert "No module named pytest" in report["final"]["output"]

    from testpilot import __main__ as cli

    def forbidden(*args, **kwargs):
        pytest.fail("saved-run comparison must not call a model or execute tests")

    monkeypatch.setattr(cli, "make_client", forbidden)
    monkeypatch.setattr(cli.TestPilot, "run", forbidden)
    raw = json.dumps(report, indent=2).encode()
    originals = [b"\xef\xbb\xbf" + raw.replace(b"\n", b"\r\n"), raw + b"\n"]
    before, after = tmp_path / "before.json", tmp_path / "after.json"
    before.write_bytes(originals[0])
    after.write_bytes(originals[1])
    output = tmp_path / "comparison.html"
    assert cli.main(["compare", "--before", str(before), "--after", str(after),
                     "--out", str(output)]) == 0
    page = output.read_text()
    downloads = re.findall(r'href="data:application/json;base64,([^"]+)"', page)
    assert [base64.b64decode(data) for data in downloads] == originals
    assert [before.read_bytes(), after.read_bytes()] == originals
    assert page.count(escape(report["final"]["summary"])) == 2
    row = re.search(r"<tr><td>Complete-suite recorded counts</td>.*?</tr>", page).group()
    assert row.count(">Unavailable as complete execution evidence<") == 2

    # Null is the producer's absent exit code; the key and integer contract stay strict.
    for value in (False, True, "0", 0.0, 1.5, -(2**53), 2**53):
        invalid = json.loads(raw)
        invalid["final"]["returncode"] = value
        with pytest.raises(ComparisonError):
            parse_report(json.dumps(invalid).encode())
    missing = json.loads(raw)
    del missing["final"]["returncode"]
    with pytest.raises(ComparisonError):
        parse_report(json.dumps(missing).encode())
