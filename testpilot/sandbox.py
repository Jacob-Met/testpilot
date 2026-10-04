"""Run pytest against a throwaway copy of a repo, with a wall-clock timeout.

Isolation is process-level only: a temp copy of the repo, a fresh process
group killed on timeout, and an environment with credential-looking variables
removed. It is NOT a security boundary against hostile code — run TestPilot in
a container/VM for untrusted repos.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path, PurePosixPath

IGNORE = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".venv", "venv",
                                "*.pyc", ".coverage", "node_modules", ".mypy_cache")
_SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
_OMIT = "*/tests/*,*/test_*.py,*_test.py,*/conftest.py"


@dataclass
class CaseResult:
    nodeid: str
    outcome: str  # passed | failed | error | skipped
    message: str = ""


@dataclass
class CoverageReport:
    percent_total: float
    files: dict[str, dict[str, list[int]]] = field(default_factory=dict)

    def executed(self, path: str) -> set[int]:
        return set(self.files.get(path, {}).get("executed", []))

    def executable(self, path: str) -> set[int]:
        f = self.files.get(path, {})
        return set(f.get("executed", [])) | set(f.get("missing", []))


@dataclass
class SandboxResult:
    returncode: int | None
    timed_out: bool
    duration_s: float
    timeout_s: float
    output: str
    cases: list[CaseResult] = field(default_factory=list)
    coverage: CoverageReport | None = None

    def _count(self, outcome: str) -> int:
        return sum(1 for c in self.cases if c.outcome == outcome)

    @property
    def passed(self) -> int:
        return self._count("passed")

    @property
    def failed(self) -> int:
        return self._count("failed")

    @property
    def errors(self) -> int:
        return self._count("error")

    @property
    def skipped(self) -> int:
        return self._count("skipped")

    @property
    def ok(self) -> bool:
        return (not self.timed_out and self.returncode == 0 and self.failed == 0
                and self.errors == 0 and self.passed > 0)

    def summary(self) -> str:
        if self.timed_out:
            return f"TIMEOUT after {self.timeout_s:g}s"
        return (f"{self.passed} passed, {self.failed} failed, {self.errors} errors, "
                f"{self.skipped} skipped (rc={self.returncode})")

    def failure_report(self, limit: int = 4000) -> str:
        parts = [self.summary()]
        if self.timed_out:
            parts.append("The test run exceeded the time limit and was killed. "
                         "Look for infinite loops, blocking I/O, or very slow tests.")
        for c in self.cases:
            if c.outcome in ("failed", "error"):
                parts.append(f"--- {c.outcome.upper()}: {c.nodeid}\n{c.message.strip()}")
        if not any(c.outcome in ("failed", "error") for c in self.cases):
            parts.append("--- pytest output (tail)\n" + self.output[-2000:])
        text = "\n".join(parts)
        return text if len(text) <= limit else text[: limit - 20] + "\n...[truncated]"

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(passed=self.passed, failed=self.failed, errors=self.errors,
                 skipped=self.skipped, ok=self.ok, summary=self.summary())
        d["output"] = self.output[-3000:]
        return d


@lru_cache(maxsize=None)
def coverage_available(python: str) -> bool:
    return subprocess.run([python, "-c", "import coverage"], capture_output=True).returncode == 0


def clean_env(root: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not any(m in k.upper() for m in _SECRET_MARKERS)}
    for k in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "COVERAGE_PROCESS_START", "COVERAGE_FILE"):
        env.pop(k, None)
    paths = [str(root / "src")] if (root / "src").is_dir() else []
    env.update(PYTHONPATH=os.pathsep.join(paths + [str(root)]), PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0")
    return env


def _run(cmd: list[str], cwd: Path, env: dict, timeout: float) -> tuple[int | None, str, bool]:
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=timeout)
        return proc.returncode, out, False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, AttributeError, PermissionError):
            proc.kill()
        out, _ = proc.communicate()
        return None, out or "", True


def parse_junit(path: Path) -> list[CaseResult]:
    root = ET.parse(path).getroot()
    cases: list[CaseResult] = []
    for tc in root.iter("testcase"):
        cls, name = tc.get("classname", ""), tc.get("name", "")
        nodeid = f"{cls}::{name}" if cls else name
        outcome, msg = "passed", ""
        for tag, label in (("failure", "failed"), ("error", "error"), ("skipped", "skipped")):
            el = tc.find(tag)
            if el is not None:
                outcome = label
                msg = (el.get("message") or "") + ("\n" + el.text if el.text else "")
                break
        cases.append(CaseResult(nodeid, outcome, msg))
    return cases


def _parse_coverage(path: Path, work: Path) -> CoverageReport:
    data = json.loads(path.read_text())
    files = {}
    resolved = work.resolve()
    for name, info in data.get("files", {}).items():
        p = Path(name)
        if p.is_absolute():
            try:
                name = p.resolve().relative_to(resolved).as_posix()
            except ValueError:
                continue
        files[PurePosixPath(name).as_posix()] = {"executed": info.get("executed_lines", []),
                                                 "missing": info.get("missing_lines", [])}
    return CoverageReport(float(data.get("totals", {}).get("percent_covered", 0.0)), files)


def _safe_join(root: Path, rel: str) -> Path:
    p = (root / rel).resolve()
    if root.resolve() not in p.parents:
        raise ValueError(f"refusing to write outside sandbox: {rel}")
    return p


def run_pytest(repo: str | Path, extra_files: dict[str, str] | None = None, *, timeout: float = 60.0,
               python: str | None = None, coverage: bool | None = None,
               pytest_args: tuple[str, ...] = ()) -> SandboxResult:
    """Copy ``repo`` to a temp dir, add ``extra_files``, run pytest, collect results."""
    python = python or sys.executable
    use_cov = coverage_available(python) if coverage is None else coverage
    with tempfile.TemporaryDirectory(prefix="testpilot-") as td:
        tdp = Path(td)
        work = tdp / "repo"
        shutil.copytree(repo, work, ignore=IGNORE)
        for rel, content in (extra_files or {}).items():
            dest = _safe_join(work, rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
        junit = tdp / "junit.xml"
        pt = ["-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir", str(work), "-o", "addopts=",
              "-o", "junit_family=xunit2", f"--junitxml={junit}", *pytest_args]
        data_file = tdp / ".coverage"
        if use_cov:
            cmd = [python, "-m", "coverage", "run", f"--data-file={data_file}", f"--source={work}",
                   f"--omit={_OMIT}", *pt]
        else:
            cmd = [python, *pt]
        env = clean_env(work)
        t0 = time.monotonic()
        rc, out, timed_out = _run(cmd, work, env, timeout)
        dur = time.monotonic() - t0
        cases = parse_junit(junit) if junit.exists() and not timed_out else []
        cov = None
        if use_cov and not timed_out:
            cov_json = tdp / "cov.json"
            crc, _, _ = _run([python, "-m", "coverage", "json", f"--data-file={data_file}", "-o", str(cov_json), "-q"],
                             work, env, 60)
            cov = _parse_coverage(cov_json, work) if crc == 0 and cov_json.exists() else CoverageReport(0.0)
        return SandboxResult(rc, timed_out, round(dur, 3), timeout, out, cases, cov)
