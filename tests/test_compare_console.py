"""Console refusal keeps the saved comparison and a stable CLI error status."""
from __future__ import annotations

import io
import os
from pathlib import Path
import subprocess
import sys

import pytest

from test_compare import raw
from testpilot.compare import read_report
from testpilot.compare_html import render_comparison


def inputs(tmp_path):
    before, after = tmp_path / "before.json", tmp_path / "after.json"
    before.write_bytes(raw())
    after.write_bytes(raw())
    expected = render_comparison(read_report(before), read_report(after)).encode("utf-8")
    return before, after, expected


def command(before, after, output, optimized=False):
    return [sys.executable, "-B"] + (["-O"] if optimized else []) + [
        "-m", "testpilot", "compare", "--before", str(before),
        "--after", str(after), "--out", str(output),
    ]


def environment(encoding="utf-8"):
    return {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": encoding}


@pytest.mark.parametrize("optimized", [False, True])
def test_closed_stdout_returns_two_and_keeps_complete_comparison(tmp_path, optimized):
    before, after, expected = inputs(tmp_path)
    output = tmp_path / "comparison.html"
    read_fd, write_fd = os.pipe()
    os.close(read_fd)
    try:
        result = subprocess.run(command(before, after, output, optimized),
                                env=environment(), stdout=write_fd,
                                stderr=subprocess.PIPE, timeout=20)
    finally:
        os.close(write_fd)
    assert result.returncode == 2
    assert result.stderr.splitlines() == [b"testpilot: comparison was written, but console delivery failed"]
    assert output.read_bytes() == expected
    assert before.read_bytes() == after.read_bytes() == raw()


@pytest.mark.parametrize("optimized", [False, True])
def test_ascii_stdout_returns_two_for_saved_unicode_path(tmp_path, optimized):
    before, after, expected = inputs(tmp_path)
    output = tmp_path / "comparison caf\u00e9.html"
    result = subprocess.run(command(before, after, output, optimized),
                            env=environment("ascii:strict"), capture_output=True, timeout=20)
    assert result.returncode == 2
    assert result.stderr.splitlines() == [b"testpilot: comparison was written, but console delivery failed"]
    assert output.read_bytes() == expected
    assert before.read_bytes() == after.read_bytes() == raw()


def test_closed_stderr_preserves_the_input_error_status(tmp_path):
    before, after, _ = inputs(tmp_path)
    before.write_bytes(b"\xff")
    output = tmp_path / "refused.html"
    read_fd, write_fd = os.pipe()
    os.close(read_fd)
    try:
        result = subprocess.run(command(before, after, output),
                                env=environment(), stdout=subprocess.PIPE,
                                stderr=write_fd, timeout=20)
    finally:
        os.close(write_fd)
    assert result.returncode == 2
    assert result.stdout == b""
    assert not output.exists()
    assert before.read_bytes() == b"\xff"
    assert after.read_bytes() == raw()


@pytest.mark.parametrize("phase", ["write", "flush"])
def test_output_write_or_flush_failure_closes_console_without_removing_html(tmp_path, monkeypatch, phase):
    from testpilot import __main__ as cli
    before, after, expected = inputs(tmp_path)
    output = tmp_path / "comparison.html"

    class FailedConsole:
        closed = False

        def write(self, text):
            if phase == "write":
                raise OSError("local output failed")
            return len(text)

        def flush(self):
            if phase == "flush":
                raise UnicodeError("local output encoding failed")

        def close(self):
            self.closed = True
            raise OSError("the failed stream also refused close")

    failed = FailedConsole()
    diagnostic = io.StringIO()
    monkeypatch.setattr(cli.sys, "stdout", failed)
    monkeypatch.setattr(cli.sys, "stderr", diagnostic)
    result = cli.main(["compare", "--before", str(before), "--after", str(after),
                       "--out", str(output)])
    assert result == 2
    assert failed.closed
    assert diagnostic.getvalue() == "testpilot: comparison was written, but console delivery failed\n"
    assert output.read_bytes() == expected
    assert before.read_bytes() == after.read_bytes() == raw()
