"""Materialize admitted final test bytes for review, without executing them."""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

from .recheck import MAX_REPORT_BYTES, RecheckError, _write_console, read_saved_tests

SCHEMA = "testpilot.export-tests/1"


class ExportTestsError(ValueError):
    """Input or complete-directory publication was refused."""


def _identity(path: Path) -> tuple[int, int, int]:
    info = path.lstat()
    return info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)


def _destination(value: str | Path) -> tuple[Path, tuple[int, int, int]]:
    raw = Path(value)
    if not raw.name or ".." in raw.parts:
        raise ExportTestsError("choose an unused output name without traversal components")
    out = raw.absolute()
    parent = out.parent
    for part in [*reversed(parent.parents), parent]:
        info = part.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise ExportTestsError("output parent must be an existing directory without symlinks")
    if os.path.lexists(out):
        raise ExportTestsError("output already exists; choose a new directory")
    return out, _identity(parent)


def _source_bytes(path: str, expected: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ExportTestsError("source report is no longer a regular file")
        data = stream.read(MAX_REPORT_BYTES + 1)
    if len(data) > MAX_REPORT_BYTES or hashlib.sha256(data).hexdigest() != expected:
        raise ExportTestsError("source report changed after admission")
    return data


def _portable_paths(tests: tuple[tuple[str, str], ...]) -> None:
    spellings: dict[str, str] = {}
    files = {name for name, _ in tests}
    for name, _ in tests:
        parts = name.split("/")
        for index in range(1, len(parts) + 1):
            prefix = "/".join(parts[:index])
            folded = prefix.casefold()
            old = spellings.setdefault(folded, prefix)
            if old != prefix:
                raise ExportTestsError("retained paths have a portable case collision")
            if index < len(parts) and prefix in files:
                raise ExportTestsError("retained paths have a file/directory conflict")


def _directory_publisher():
    # POSIX rename can replace an existing empty directory. It is not a safe
    # fallback for this command's explicit create-only destination contract.
    if not sys.platform.startswith("linux"):
        raise ExportTestsError("atomic create-only directory export is currently supported on Linux")
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, "renameat2", None)
    if rename is None:
        raise ExportTestsError("Linux renameat2 is unavailable; no output was published")
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int

    def publish(stage: Path, out: Path) -> None:
        # AT_FDCWD=-100 and RENAME_NOREPLACE=1. Same-parent staging also keeps
        # publication on one filesystem. Kernel refusal leaves the target intact.
        if rename(-100, os.fsencode(stage), -100, os.fsencode(out), 1) != 0:
            code = ctypes.get_errno()
            raise OSError(code, os.strerror(code), str(out))

    return publish


def _write_bytes(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def export_saved_tests(report_path: str | Path, out_dir: str | Path) -> dict:
    """Publish exact retained final tests and provenance in one new directory.

    Historical status does not qualify these tests as passing. The original
    report is copied byte-for-byte so all other recorded metadata stays available.
    No model, test runner, project checkout or patch application is invoked.
    """
    stage: Path | None = None
    stage_identity = None
    try:
        out, parent_identity = _destination(out_dir)
        publish = _directory_publisher()
        saved = read_saved_tests(report_path)
        source = _source_bytes(saved.path, saved.sha256)
        _portable_paths(saved.tests)
        payloads = [(name, content.encode("utf-8")) for name, content in saved.tests]
        manifest = {
            "schema": SCHEMA,
            "status": "exported_for_review",
            "source_report": {
                "path": saved.path,
                "sha256": saved.sha256,
                "recorded_status": saved.source_status,
                "copy": "source-report.json",
            },
            "test_files": [
                {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                for name, data in payloads
            ],
            "test_runs": 0,
            "model_calls": 0,
            "scope": "Exact admitted final test bytes for review; historical status is not a new execution result.",
        }
        manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=True) + "\n").encode("utf-8")
        stage = Path(tempfile.mkdtemp(prefix=".testpilot-export-", dir=out.parent))
        stage_identity = _identity(stage)
        for name, data in payloads:
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            _write_bytes(target, data)
        _write_bytes(stage / "source-report.json", source)
        _write_bytes(stage / "export-manifest.json", manifest_bytes)
        if _identity(out.parent) != parent_identity or _identity(stage) != stage_identity:
            raise ExportTestsError("output parent or private staging identity changed")
        _source_bytes(saved.path, saved.sha256)
        publish(stage, out)
        stage = None
        return manifest
    except (OSError, RecheckError, UnicodeError) as exc:
        raise ExportTestsError(f"cannot export retained tests: {exc}") from exc
    finally:
        if stage is not None and stage.exists() and _identity(stage) == stage_identity:
            shutil.rmtree(stage)


def run_export_tests_command(args) -> int:
    try:
        manifest = export_saved_tests(args.report, args.out)
    except (ExportTestsError, OSError) as exc:
        _write_console(sys.stderr, json.dumps({"ok": False, "error": str(exc)}) + "\n")
        return 2
    summary = {"ok": True, "output": str(Path(args.out).absolute()),
               "files": len(manifest["test_files"]), "source_report": manifest["source_report"],
               "test_runs": 0, "model_calls": 0, "status": manifest["status"]}
    if not _write_console(sys.stdout, json.dumps(summary) + "\n"):
        _write_console(sys.stderr, "testpilot: export was published, but console delivery failed\n")
        return 2
    return 0
