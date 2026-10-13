"""Target preview output is complete or an explicit CLI delivery failure."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from testpilot import __main__ as cli


ROOT = Path(__file__).resolve().parents[1]
MESSAGE = "testpilot: cannot write target preview\n"
SOURCE = "def double(value):\n    return value * 2\n"
DIFF = "--- a/math.py\n+++ b/math.py\n@@ -1,2 +1,2 @@\n def double(value):\n-    return value\n+    return value * 2\n"


@pytest.fixture
def preview(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    subject = project / "math.py"
    subject.write_text(SOURCE, encoding="utf-8")
    diff = tmp_path / "change.diff"
    diff.write_text(DIFF, encoding="utf-8")
    return ["targets", "--repo", str(project), "--diff", str(diff)]


class FailedStream:
    def __init__(self, phase, error, *, close_error=False):
        self.phase = phase
        self.error = error
        self.close_error = close_error
        self.closed = False
        self.parts = []

    def write(self, value):
        if self.phase == "write":
            raise self.error
        self.parts.append(value)
        return len(value)

    def flush(self):
        if self.phase == "flush":
            raise self.error

    def close(self):
        self.closed = True
        if self.close_error:
            raise self.error


class RecordingStream(io.StringIO):
    def __init__(self):
        super().__init__()
        self.flushes = 0

    def flush(self):
        self.flushes += 1
        super().flush()


@pytest.mark.parametrize("json_output", [False, True])
@pytest.mark.parametrize("phase", ["write", "flush"])
@pytest.mark.parametrize("error", [OSError("destination unavailable"), UnicodeError("destination encoding")])
def test_failed_delivery_is_status_two_and_closes_stdout(preview, monkeypatch, json_output, phase, error):
    output = FailedStream(phase, error, close_error=True)
    errors = io.StringIO()

    def forbidden(*args, **kwargs):
        raise AssertionError("target preview entered generation or test execution")

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        patch.setattr(sys, "stderr", errors)
        patch.setattr(cli, "make_client", forbidden)
        patch.setattr(cli, "TestPilot", forbidden)
        patch.setattr(cli, "write_outputs", forbidden)
        patch.setattr(cli.subprocess, "run", forbidden)
        status = cli.main(preview + (["--json"] if json_output else []))

    assert status == 2
    assert output.closed
    assert errors.getvalue() == MESSAGE
    project = Path(preview[2])
    assert [p.name for p in project.iterdir()] == ["math.py"]
    assert (project / "math.py").read_text(encoding="utf-8") == SOURCE


@pytest.mark.parametrize("phase", ["write", "flush"])
def test_failed_stderr_cannot_replace_output_failure(preview, monkeypatch, phase):
    output = FailedStream("flush", BrokenPipeError("closed output pipe"))
    errors = FailedStream(phase, OSError("closed diagnostic pipe"), close_error=True)
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        patch.setattr(sys, "stderr", errors)
        status = cli.main(preview)
    assert status == 2
    assert output.closed and errors.closed


@pytest.mark.parametrize("json_output", [False, True])
def test_successful_output_keeps_exact_content_and_flushes(preview, monkeypatch, json_output):
    output, errors = RecordingStream(), io.StringIO()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        patch.setattr(sys, "stderr", errors)
        status = cli.main(preview + (["--json"] if json_output else []))
    assert status == 0
    assert not output.closed and output.flushes == 1
    assert errors.getvalue() == ""
    if json_output:
        expected = {"changed_functions": [{
            "path": "math.py", "module": "math", "qualname": "double", "lineno": 1,
            "end_lineno": 2, "changed_lines": [2],
            "source": "def double(value):\n    return value * 2", "is_method": False,
        }]}
        assert output.getvalue() == json.dumps(expected, indent=2) + "\n"
    else:
        assert output.getvalue() == '1 changed Python function outside tests\n"math.py":1-2  "double"\n'


@pytest.mark.parametrize("json_output", [False, True])
def test_actual_cli_closed_pipe_preserves_status_two(preview, json_output):
    command = [sys.executable, "-B", "-m", "testpilot", *preview]
    if json_output:
        command.append("--json")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    read_end, write_end = os.pipe()
    os.close(read_end)
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=write_end,
                                stderr=subprocess.PIPE, timeout=15)
    finally:
        os.close(write_end)
    assert result.returncode == 2
    assert result.stderr == MESSAGE.encode("utf-8")


def test_unrelated_output_exceptions_still_propagate(preview, monkeypatch):
    output = FailedStream("write", RuntimeError("unexpected stream defect"))
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        with pytest.raises(RuntimeError, match="unexpected stream defect"):
            cli.main(preview)
    assert not output.closed
