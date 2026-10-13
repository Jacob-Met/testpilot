"""Optional live phase notices for the unchanged generation loop."""
from __future__ import annotations

import sys
from pathlib import Path

from .loop import Ledger, TestPilot
from .sandbox import SandboxResult


class ProgressTestPilot(TestPilot):
    """Delegate normal work and emit bounded, best-effort notices to stderr."""

    def _emit(self, message: str) -> None:
        if getattr(self, "_progress_disabled", False):
            return
        stream = sys.stderr
        if stream is None:
            # print(file=None) would silently send optional notices to stdout.
            self._progress_disabled = True
            return
        try:
            print(f"[testpilot] {message}", file=stream, flush=True)
        except (OSError, UnicodeError, ValueError):
            # Progress is optional. A failed destination must not stop test work
            # or leave buffered output that changes the process exit at shutdown.
            self._progress_disabled = True
            try:
                stream.close()
            except (OSError, UnicodeError, ValueError):
                pass

    def _ask(self, ledger: Ledger, role: str, system: str, user: str) -> str:
        phase = {"planner": "Planning tests", "editor": "Generating tests",
                 "repair": "Repairing tests"}.get(role, "Model phase")
        self._emit(f"{phase}: starting")
        response = super()._ask(ledger, role, system, user)
        self._emit(f"{phase}: completed")
        return response

    def _run(self, repo: Path, files: dict[str, str] | None) -> SandboxResult:
        phase = "Baseline pytest" if files is None else "Generated pytest"
        self._emit(f"{phase}: running")
        result = super()._run(repo, files)
        if result.timed_out:
            detail = "timed out"
        elif not result.junit_available:
            detail = f"finished without usable JUnit (rc={result.returncode})"
        else:
            detail = (f"finished: {result.passed} passed, {result.failed} failed, "
                      f"{result.errors} errors, {result.skipped} skipped "
                      f"(rc={result.returncode})")
        self._emit(f"{phase}: {detail}")
        return result
