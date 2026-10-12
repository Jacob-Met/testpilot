"""Windows cancellation must bound leader cleanup without touching its pipe."""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from testpilot import sandbox


class WindowsInterruptTests(unittest.TestCase):
    def run_with(self, proc):
        with patch.object(sandbox, "os", SimpleNamespace(name="nt")), \
                patch.object(sandbox.subprocess, "Popen", return_value=proc) as popen:
            result = sandbox._run(["owned-child"], Path("."), {"FIXTURE": "1"}, 12.0)
        return result, popen

    def interrupted(self, proc, cancellation):
        with self.assertRaises(KeyboardInterrupt) as caught:
            self.run_with(proc)
        self.assertIs(caught.exception, cancellation)
        proc.stdout.close.assert_not_called()

    def proc(self, cancellation):
        proc = Mock()
        proc.returncode = None
        proc.communicate.side_effect = cancellation
        return proc

    def test_finite_result_and_popen_arguments_preserved(self):
        proc = Mock(returncode=7)
        proc.communicate.return_value = ("stdout\nstderr\n", None)
        result, popen = self.run_with(proc)
        self.assertEqual(result, (7, "stdout\nstderr\n", False))
        proc.communicate.assert_called_once_with(timeout=12.0)
        proc.kill.assert_not_called()
        proc.wait.assert_not_called()
        proc.stdout.close.assert_not_called()
        popen.assert_called_once_with(
            ["owned-child"], cwd=Path("."), env={"FIXTURE": "1"},
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, errors="replace",
            start_new_session=True,
        )

    def test_timeout_branch_keeps_existing_windows_behavior(self):
        proc = Mock(returncode=None)
        proc.communicate.side_effect = [
            subprocess.TimeoutExpired(["owned-child"], 12.0),
            ("partial\r\n", None),
        ]
        result, _ = self.run_with(proc)
        self.assertEqual(result, (None, "partial\r\n", True))
        self.assertEqual(proc.communicate.call_args_list, [
            call(timeout=12.0), call(timeout=None),
        ])
        proc.kill.assert_called_once_with()
        proc.wait.assert_not_called()
        proc.stdout.close.assert_not_called()

    def test_interrupt_kills_then_waits_without_touching_reader(self):
        cancellation = KeyboardInterrupt("caller-owned cancellation")
        proc = self.proc(cancellation)
        calls = []
        proc.kill.side_effect = lambda: calls.append("kill")
        proc.wait.side_effect = lambda *, timeout: calls.append(("wait", timeout))
        self.interrupted(proc, cancellation)
        self.assertEqual(calls, ["kill", ("wait", 1.0)])
        proc.kill.assert_called_once_with()
        proc.wait.assert_called_once_with(timeout=1.0)
        proc.communicate.assert_called_once_with(timeout=12.0)

    def test_already_exited_leader_keeps_its_original_exit(self):
        cancellation = KeyboardInterrupt("already exited")
        proc = self.proc(cancellation)
        proc.returncode = 23
        proc.wait.return_value = 23
        self.interrupted(proc, cancellation)
        self.assertEqual(proc.returncode, 23)
        proc.kill.assert_called_once_with()
        proc.wait.assert_called_once_with(timeout=1.0)

    def test_kill_oserror_does_not_replace_cancellation(self):
        cancellation = KeyboardInterrupt("kill failed")
        proc = self.proc(cancellation)
        proc.kill.side_effect = OSError("owned leader no longer available")
        self.interrupted(proc, cancellation)
        proc.kill.assert_called_once_with()
        proc.wait.assert_not_called()

    def test_wait_oserror_does_not_replace_cancellation(self):
        cancellation = KeyboardInterrupt("wait failed")
        proc = self.proc(cancellation)
        proc.wait.side_effect = OSError("owned wait failed")
        self.interrupted(proc, cancellation)
        proc.kill.assert_called_once_with()
        proc.wait.assert_called_once_with(timeout=1.0)

    def test_wait_timeout_does_not_replace_cancellation(self):
        cancellation = KeyboardInterrupt("wait timed out")
        proc = self.proc(cancellation)
        proc.wait.side_effect = subprocess.TimeoutExpired(["owned-child"], 1.0)
        self.interrupted(proc, cancellation)
        proc.kill.assert_called_once_with()
        proc.wait.assert_called_once_with(timeout=1.0)

    def test_retained_pipe_is_not_drained_joined_or_closed(self):
        cancellation = KeyboardInterrupt("retained helper pipe")
        proc = self.proc(cancellation)
        proc.stdout.close.side_effect = AssertionError("would wait for reader lock")
        proc.stdout_thread = Mock()
        self.interrupted(proc, cancellation)
        proc.stdout_thread.join.assert_not_called()
        proc.communicate.assert_called_once_with(timeout=12.0)
        proc.wait.assert_called_once_with(timeout=1.0)


if __name__ == "__main__":
    unittest.main()
