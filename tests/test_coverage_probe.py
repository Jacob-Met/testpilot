"""Optional coverage detection uses real, isolated interpreter imports."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from testpilot import sandbox


class CoverageProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="testpilot-probe-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.module = self.root / "coverage.py"
        self.marker = self.root / "imported.txt"
        self.env = patch.dict(os.environ, {
            "PYTHONPATH": str(self.root),
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        sandbox.coverage_available.cache_clear()
        self.addCleanup(sandbox.coverage_available.cache_clear)

    def write_module(self, code):
        self.module.write_text(code, encoding="utf-8")

    def test_success_is_cached_for_the_selected_interpreter(self):
        self.write_module(
            "from pathlib import Path\n"
            f"with Path({str(self.marker)!r}).open('a') as f: f.write('imported\\n')\n"
        )
        self.assertTrue(sandbox.coverage_available(sys.executable))
        self.assertTrue(sandbox.coverage_available(sys.executable))
        self.assertEqual(self.marker.read_text(), "imported\n")

    def test_failed_import_is_unavailable(self):
        self.write_module("raise RuntimeError('synthetic unavailable coverage')\n")
        self.assertFalse(sandbox.coverage_available(sys.executable))

    def test_slow_import_is_killed_and_reports_unavailable(self):
        finished = self.root / "finished.txt"
        self.write_module(
            "import os, time\nfrom pathlib import Path\n"
            f"Path({str(self.marker)!r}).write_text(str(os.getpid()))\n"
            "time.sleep(1.5)\n"
            f"Path({str(finished)!r}).write_text('finished')\n"
        )
        started = time.monotonic()
        with patch.object(sandbox, "_COVERAGE_PROBE_TIMEOUT_S", 0.3, create=True):
            available = sandbox.coverage_available(sys.executable)
        elapsed = time.monotonic() - started
        self.assertFalse(available)
        self.assertLess(elapsed, 1.3)
        self.assertTrue(self.marker.is_file(), "the real import must have started")
        self.assertFalse(finished.exists())
        if os.name == "posix":
            pid = int(self.marker.read_text())
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)

    def test_probe_has_closed_stdin_and_discards_unused_output(self):
        self.write_module(
            "import sys\nfrom pathlib import Path\n"
            f"Path({str(self.marker)!r}).write_text(sys.stdin.read())\n"
            "sys.stdout.write('out' * 100_000)\n"
            "sys.stderr.write('err' * 100_000)\n"
        )
        with patch.object(sandbox.subprocess, "run", wraps=subprocess.run) as run:
            self.assertTrue(sandbox.coverage_available(sys.executable))
        self.assertEqual(self.marker.read_text(), "")
        self.assertEqual(run.call_args.args[0], [sys.executable, "-c", "import coverage"])
        self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(run.call_args.kwargs["stdout"], subprocess.DEVNULL)
        self.assertEqual(run.call_args.kwargs["stderr"], subprocess.DEVNULL)
        self.assertEqual(run.call_args.kwargs["timeout"], 5.0)

    def test_interpreter_start_errors_remain_errors(self):
        with self.assertRaises(FileNotFoundError):
            sandbox.coverage_available(str(self.root / "missing-python"))


if __name__ == "__main__":
    unittest.main()
