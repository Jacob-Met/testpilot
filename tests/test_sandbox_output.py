"""Real POSIX children exercise bounded output and the ordinary pytest consumer."""
import os
import sys
import time
import tracemalloc

import pytest

from testpilot.sandbox import _run, clean_env, run_pytest


pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX bounded pipe collection")
TAIL_BYTES = 256 * 1024


@pytest.mark.parametrize("size", [0, TAIL_BYTES - 1, TAIL_BYTES, TAIL_BYTES + 1])
def test_retained_output_boundary(tmp_path, size):
    program = "import os,sys; os.write(1,b'x'*int(sys.argv[1]))"
    rc, output, timed_out = _run(
        [sys.executable, "-c", program, str(size)], tmp_path, clean_env(tmp_path), 5
    )
    assert rc == 0 and not timed_out
    if size <= TAIL_BYTES:
        assert output == "x" * size
    else:
        assert output == "[testpilot: omitted 1 earlier output bytes]\n" + "x" * TAIL_BYTES


def test_noisy_child_keeps_final_diagnostic_with_bounded_parent_allocations(tmp_path):
    program = (
        "import os; chunk=b'x'*65536; "
        "[os.write(1,chunk) for _ in range(256)]; "
        "os.write(2,b'FINAL-DIAGNOSTIC\\n')"
    )
    tracemalloc.start()
    try:
        rc, output, timed_out = _run(
            [sys.executable, "-c", program], tmp_path, clean_env(tmp_path), 10
        )
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    final = "FINAL-DIAGNOSTIC\n"
    emitted = 16 * 1024 * 1024 + len(final)
    assert rc == 0 and not timed_out
    assert output == (
        f"[testpilot: omitted {emitted - TAIL_BYTES} earlier output bytes]\n"
        + "x" * (TAIL_BYTES - len(final)) + final
    )
    # The predecessor retains and copies all 16 MiB. This leaves generous room
    # for pipe chunks, decoding and process setup while detecting that behavior.
    assert peak < 8 * 1024 * 1024, f"parent retained {peak:,} bytes during output collection"


def test_timeout_retains_one_bounded_tail_then_fresh_run_succeeds(tmp_path):
    program = (
        "import os,time; chunk=b'x'*65536; "
        "[os.write(1,chunk) for _ in range(32)]; "
        "os.write(1,b'LAST-BEFORE-WAIT\\n'); time.sleep(20)"
    )
    started = time.monotonic()
    rc, output, timed_out = _run(
        [sys.executable, "-c", program], tmp_path, clean_env(tmp_path), 0.4
    )
    assert timed_out and rc is None
    assert output.count("[testpilot: omitted ") == 1
    assert output.endswith("LAST-BEFORE-WAIT\n")
    assert len(output) <= TAIL_BYTES + 100
    assert time.monotonic() - started < 2.5
    assert _run([sys.executable, "-c", "print('recovered')"],
                tmp_path, clean_env(tmp_path), 5) == (0, "recovered\n", False)


@pytest.mark.parametrize("timeout,expected", [
    (5, (7, "", False)), (None, (7, "", False)), (0.1, (None, "", True)),
])
def test_stdout_eof_does_not_replace_process_exit_or_deadline(tmp_path, timeout, expected):
    program = "import os,time; os.close(1); os.close(2); time.sleep(0.3); raise SystemExit(7)"
    assert _run([sys.executable, "-c", program], tmp_path, clean_env(tmp_path), timeout) == expected


def test_truncated_multibyte_prefix_keeps_complete_final_text(tmp_path):
    program = "import os; os.write(1,b'\\xe2\\x82\\xac'*87400+b'last\\n')"
    rc, output, timed_out = _run(
        [sys.executable, "-c", program], tmp_path, clean_env(tmp_path), 5
    )
    assert rc == 0 and not timed_out
    prefix, tail = output.split("\n", 1)
    assert prefix == "[testpilot: omitted 61 earlier output bytes]"
    assert tail.startswith("\ufffd\ufffd")  # The retained byte range starts inside a UTF-8 scalar.
    assert tail.endswith("last\n")
    assert tail[2:-5] == "\u20ac" * 87379


def test_real_pytest_result_survives_verbose_native_output(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    test = repo / "test_noisy.py"
    source = (
        "import os\n"
        "def test_noisy():\n"
        "    for _ in range(32):\n"
        "        os.write(1, b'x' * 65536)\n"
        "    os.write(2, b'\\nNATIVE-PYTEST-TAIL\\n')\n"
        "    assert 6 * 7 == 42\n"
    )
    test.write_text(source)
    result = run_pytest(repo, timeout=10, coverage=False, pytest_args=("-s",))
    assert result.ok and result.passed == 1 and result.junit_available
    assert result.output.startswith("[testpilot: omitted ")
    assert "NATIVE-PYTEST-TAIL" in result.output
    assert len(result.output) <= TAIL_BYTES + 100
    assert test.read_text() == source
