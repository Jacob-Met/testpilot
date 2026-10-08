"""Real subprocess controls for timeout cleanup when a helper retains stdout."""
import os
from pathlib import Path
import signal
import sys
import time

import pytest

from testpilot.sandbox import _run, clean_env, run_pytest


POSIX = pytest.mark.skipif(os.name != "posix", reason="POSIX process groups and detached sessions")
HELPER = "import time; time.sleep(6)"
PARENT = """\
import os, pathlib, subprocess, sys, time
child = subprocess.Popen([sys.executable, '-c', sys.argv[2]], start_new_session=True)
pathlib.Path(sys.argv[1]).write_text(str(child.pid))
os.write(1, bytes.fromhex(sys.argv[3]))
if sys.argv[4] == 'wait':
    time.sleep(20)
"""


def stop_helper(marker: Path) -> None:
    if marker.exists():
        try:
            os.killpg(int(marker.read_text()), signal.SIGKILL)
        except ProcessLookupError:
            pass


def run_with_helper(tmp_path: Path, *, exits: bool = False, output: bytes = b"parent-ready\n"):
    marker = tmp_path / "helper.pid"
    started = time.monotonic()
    try:
        result = _run(
            [sys.executable, "-c", PARENT, str(marker), HELPER, output.hex(),
             "exit" if exits else "wait"],
            tmp_path, clean_env(tmp_path), 0.4,
        )
        elapsed = time.monotonic() - started
        assert marker.exists(), "the receiving helper must actually start"
        return result, elapsed
    finally:
        # The helper deliberately leaves the target process group. This receiver
        # owns and kills it; the sandbox does not claim to contain escaped children.
        stop_helper(marker)


def test_combined_output_and_returncode_remain_available(tmp_path):
    program = (
        "import os; os.write(1, b'normal output\\r\\n'); "
        "os.write(2, b'diagnostic\\r\\n'); raise SystemExit(7)"
    )
    assert _run([sys.executable, "-c", program], tmp_path, clean_env(tmp_path), 5) == (
        7, "normal output\ndiagnostic\n", False,
    )


@POSIX
@pytest.mark.parametrize("parent_exits", [False, True])
def test_timeout_finishes_when_detached_helper_retains_pipe(tmp_path, parent_exits):
    result, elapsed = run_with_helper(tmp_path, exits=parent_exits)
    assert result == (None, "parent-ready\n", True)
    assert elapsed < 2.5, f"0.4-second timeout waited {elapsed:.3f}s for a detached helper"


@POSIX
def test_timeout_preserves_partial_multibyte_diagnostics(tmp_path):
    result, elapsed = run_with_helper(tmp_path, output=b"complete caf\xc3\xa9\r\npartial: \xe2")
    assert result == (None, "complete caf\u00e9\npartial: \ufffd", True)
    assert elapsed < 2.5, f"partial output kept timeout cleanup blocked for {elapsed:.3f}s"


def test_empty_timeout_output_stays_empty(tmp_path):
    result = _run([sys.executable, "-c", "import time; time.sleep(20)"],
                  tmp_path, clean_env(tmp_path), 0.2)
    assert result == (None, "", True)


@POSIX
def test_real_pytest_timeout_then_fresh_success(tmp_path):
    repo = tmp_path / "source"
    repo.mkdir()
    marker = tmp_path / "pytest-helper.pid"
    test_file = repo / "test_server.py"
    source = f"""\
import pathlib, subprocess, sys, time

def test_server(capfd):
    with capfd.disabled():
        child = subprocess.Popen([sys.executable, '-c', {HELPER!r}], start_new_session=True)
        pathlib.Path({str(marker)!r}).write_text(str(child.pid))
        print('pytest-helper-started', flush=True)
        time.sleep(20)
"""
    test_file.write_text(source)
    started = time.monotonic()
    try:
        result = run_pytest(repo, timeout=1, coverage=False)
        elapsed = time.monotonic() - started
        assert marker.exists(), "the actual pytest test must start its helper"
        assert result.timed_out and result.returncode is None and not result.ok
        assert result.cases == []
        assert "pytest-helper-started" in result.output
        assert "TIMEOUT" in result.failure_report()
        assert test_file.read_text() == source
        assert elapsed < 3.5, f"one-second pytest timeout waited {elapsed:.3f}s"
    finally:
        stop_helper(marker)

    test_file.write_text("def test_fresh():\n    assert 6 * 7 == 42\n")
    fresh = run_pytest(repo, timeout=10, coverage=False)
    assert fresh.ok and fresh.passed == 1 and not fresh.timed_out
