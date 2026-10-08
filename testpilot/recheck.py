"""Run a saved report's exact generated tests without calling a model.

The existing sandbox and generated-case collector determine execution results.
This module admits retained test bytes and keeps this result separate from the
original generation report.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from .sandbox import run_pytest

SCHEMA = "testpilot.recheck/1"
MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_TEST_BYTES = 4 * 1024 * 1024
MAX_TEST_FILES = 128
_TEST_PATH = re.compile(r"tests/(?:[A-Za-z0-9_]+/)*test_[A-Za-z0-9_]+\.py")


class RecheckError(ValueError):
    """The saved tests cannot be admitted or the check cannot be completed."""


@dataclass(frozen=True)
class SavedTests:
    path: str
    sha256: str
    source_status: str | None
    tests: tuple[tuple[str, str], ...]


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise RecheckError(f"saved report has duplicate JSON key {key!r}")
        obj[key] = value
    return obj


def _reject_constant(value: str) -> None:
    raise RecheckError(f"saved report contains non-finite JSON number {value}")


def read_saved_tests(report_path: str | Path) -> SavedTests:
    """Read bounded UTF-8 JSON once; never use its recorded success as evidence."""
    path = Path(report_path)
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode):
        raise RecheckError("saved report must be a regular file")
    if metadata.st_size > MAX_REPORT_BYTES:
        raise RecheckError(f"saved report exceeds {MAX_REPORT_BYTES} bytes")
    # O_NONBLOCK also prevents a POSIX FIFO substituted after the path check
    # from blocking at open. Recheck descriptor type and read an explicit bound.
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise RecheckError("saved report must be a regular file")
        data = stream.read(MAX_REPORT_BYTES + 1)
    if len(data) > MAX_REPORT_BYTES:
        raise RecheckError(f"saved report exceeds {MAX_REPORT_BYTES} bytes")
    try:
        document = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                              parse_constant=_reject_constant)
    except RecheckError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise RecheckError(f"cannot read saved report as UTF-8 JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise RecheckError("saved report must be a JSON object")
    if document.get("schema") not in (None, SCHEMA):
        raise RecheckError("unsupported saved recheck schema")
    files = document.get("test_files")
    if not isinstance(files, dict) or not files or len(files) > MAX_TEST_FILES:
        raise RecheckError(f"saved report must contain 1 to {MAX_TEST_FILES} test_files")
    total = 0
    for rel, content in files.items():
        if not isinstance(rel, str) or not _TEST_PATH.fullmatch(rel):
            raise RecheckError(f"unsupported retained test path {rel!r}")
        if not isinstance(content, str):
            raise RecheckError(f"retained test {rel!r} must contain text")
        try:
            total += len(content.encode("utf-8"))
        except UnicodeError as exc:
            raise RecheckError(f"retained test {rel!r} is not valid UTF-8 text") from exc
        if total > MAX_TEST_BYTES:
            raise RecheckError(f"retained test contents exceed {MAX_TEST_BYTES} UTF-8 bytes")
    status = document.get("status")
    return SavedTests(str(path.absolute()), hashlib.sha256(data).hexdigest(),
                      status if isinstance(status, str) else None,
                      tuple(sorted(files.items())))


def _placement(repo: Path, rel: str, data: bytes) -> str:
    """Accept an absent path or exactly matching regular file, without following links."""
    cursor = repo
    parts = PurePosixPath(rel).parts
    for index, part in enumerate(parts):
        cursor /= part
        try:
            metadata = cursor.lstat()
        except FileNotFoundError:
            return "temporary"
        if stat.S_ISLNK(metadata.st_mode):
            raise RecheckError(f"retained test path traverses a symlink: {rel!r}")
        if index != len(parts) - 1:
            if not stat.S_ISDIR(metadata.st_mode):
                raise RecheckError(f"retained test parent is not a directory: {rel!r}")
        else:
            if not stat.S_ISREG(metadata.st_mode):
                raise RecheckError(f"retained test path is not a regular file: {rel!r}")
            if metadata.st_size != len(data):
                raise RecheckError(f"existing test differs from the saved bytes: {rel!r}")
            with cursor.open("rb") as stream:
                if stream.read(len(data) + 1) != data:
                    raise RecheckError(f"existing test differs from the saved bytes: {rel!r}")
    return "already_present"


def recheck_report(repo: str | Path, report_path: str | Path, *,
                   timeout_s: float = 60.0, python: str | None = None) -> dict:
    """Execute exact retained tests in the native throwaway project copy.

    Existing matching tests stay part of the normal configured suite and the
    generated-file manifest. Different current test bytes refuse before pytest;
    they are never renamed, overwritten or treated as the retained tests.
    """
    if (isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float))
            or not math.isfinite(timeout_s) or timeout_s <= 0):
        raise RecheckError("timeout must be a positive finite number of seconds")
    project = Path(repo).resolve(strict=True)
    if not project.is_dir():
        raise RecheckError("repository must be a directory")
    saved = read_saved_tests(report_path)
    files = dict(saved.tests)
    retained = []
    for rel, content in saved.tests:
        data = content.encode("utf-8")
        retained.append({"path": rel, "bytes": len(data),
                         "sha256": hashlib.sha256(data).hexdigest(),
                         "placement": _placement(project, rel, data)})
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        # This is a test recheck, not a comparison with historical coverage.
        # The same selected suite and native generated-case rules still apply.
        result = run_pytest(project, files, timeout=timeout_s, python=python,
                            coverage=False, exact_files=True)
    except (OSError, ValueError, ET.ParseError) as exc:
        raise RecheckError(f"cannot complete retained-test execution: {exc}") from exc
    # Recheck placement before emitting a result. Concurrent checkout edits
    # are not silently described as the admitted retained version.
    for item in retained:
        if _placement(project, item["path"], files[item["path"]].encode("utf-8")) != item["placement"]:
            raise RecheckError(f"retained test placement changed during execution: {item['path']!r}")
    if result.ok:
        status = "passed"
    elif (result.junit_available and not result.timed_out and result.returncode in (0, 5)
          and not result.failed and not result.errors):
        status = "no_tests"
    else:
        status = "failed"
    return {
        "schema": SCHEMA,
        "status": status,
        "ok": result.ok,
        "repo": str(project),
        "python": python or sys.executable,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "source_report": {"path": saved.path, "sha256": saved.sha256,
                          "recorded_status": saved.source_status},
        "test_files": files,
        "retained_tests": retained,
        "final": result.to_dict(),
        "model_calls": 0,
        "scope": "Current selected-suite execution of exact retained tests; no new model calls or historical coverage comparison.",
    }


def render_recheck(result: dict) -> str:
    """Human-readable current result; original model conclusions stay historical."""
    lines = [
        f"# TestPilot recheck: **{result['status']}**",
        "",
        f"- Current run: {result['final']['summary']}",
        f"- Retained test files: {len(result['retained_tests'])}",
        f"- Project Python: {json.dumps(result['python'])}",
        "- New model calls: 0",
        f"- Source report SHA-256: {result['source_report']['sha256']}",
        "",
        "This result reruns the saved tests against the current checkout. It does not",
        "reaffirm the original model diagnosis or compare historical coverage.",
        "The source report and repository are not written by the recheck command.",
        "",
        "## Retained files",
        "",
    ]
    for item in result["retained_tests"]:
        lines.append(f"- {json.dumps(item['path'])}: {item['placement']}; SHA-256 {item['sha256']}")
    return "\n".join(lines) + "\n"


def _output_destination(repo: str | Path, out_dir: str | Path) -> Path:
    out = Path(out_dir)
    if out.exists() or out.is_symlink():
        raise RecheckError("recheck output path already exists; choose a new --out directory")
    out = out.resolve()
    project = Path(repo).resolve(strict=True)
    if out == project or project in out.parents:
        raise RecheckError("recheck output must be outside the repository being checked")
    return out


def write_recheck_outputs(result: dict, out_dir: str | Path) -> dict[str, Path]:
    """Create separate results, leaving original reports and patches untouched."""
    out = _output_destination(result["repo"], out_dir)
    out.mkdir(parents=True, exist_ok=False)
    paths = {"md": out / "recheck.md", "json": out / "recheck.json"}
    paths["md"].write_text(render_recheck(result), encoding="utf-8")
    paths["json"].write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return paths


def _write_console(stream, text: str) -> bool:
    try:
        stream.write(text)
        stream.flush()
        return True
    except (OSError, UnicodeError):
        # A failed buffered stream must not fail again during process shutdown
        # and replace our output-error status. This only closes a failed stream.
        try:
            stream.close()
        except (OSError, UnicodeError):
            pass
        return False


def run_recheck_command(args) -> int:
    """CLI boundary: input/output failures remain distinct from failed tests."""
    try:
        out = _output_destination(args.repo, args.out)
        result = recheck_report(args.repo, args.report, timeout_s=args.timeout, python=args.python)
        paths = write_recheck_outputs(result, out)
    except (OSError, RecheckError) as exc:
        _write_console(sys.stderr, f"testpilot: cannot recheck saved tests: {exc}\n")
        return 2
    summary = (f"TestPilot recheck: {result['status']}\n"
               f"{result['final']['summary']}\n"
               "New model calls: 0\n"
               f"wrote {', '.join(str(p) for p in paths.values())}\n")
    if not _write_console(sys.stdout, summary):
        _write_console(sys.stderr, "testpilot: recheck results were written, but console delivery failed\n")
        return 2
    return 0 if result["ok"] else 1
