"""Reopen an explicitly selected saved generation report and matching patch.

This consumer preserves the native renderer. It checks the artifact transport
and renderable layout, not the truth of the recorded execution or diagnosis.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import tempfile

from .html_report import render_html_report

MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_PATCH_BYTES = 4 * 1024 * 1024


class SavedReportError(ValueError):
    """A saved artifact pair cannot be reopened as a native review."""


def _read_file(path: Path, limit: int, label: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise SavedReportError(f"{label} must be a regular file")
        if metadata.st_size > limit:
            raise SavedReportError(f"{label} exceeds {limit} bytes")
        chunks = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(descriptor, min(remaining, 65536))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > limit:
            raise SavedReportError(f"{label} exceeds {limit} bytes")
        return data
    finally:
        os.close(descriptor)


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise SavedReportError(f"report has duplicate JSON key {key!r}")
        result[key] = value
    return result


def _finite_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise SavedReportError("report contains a non-finite JSON number")
    return result


def _reject_constant(value: str) -> None:
    raise SavedReportError(f"report contains non-finite JSON number {value}")


def _objects(value: object, label: str) -> list[dict]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise SavedReportError(f"{label} must be an array of objects")
    return value


def _files(value: object, label: str) -> None:
    if not isinstance(value, dict) or any(not isinstance(text, str) for text in value.values()):
        raise SavedReportError(f"{label} must map file names to text")


def _booleans(record: dict, names: tuple[str, ...], label: str) -> None:
    for name in names:
        if name in record and not isinstance(record[name], bool):
            raise SavedReportError(f"{label}.{name} must be a boolean")


def _run_layout(value: object, label: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise SavedReportError(f"{label} must be an object or null")
    _booleans(value, ("junit_available", "timed_out"), label)
    _objects(value.get("cases", []), label + ".cases")
    if value.get("generated") is not None and not isinstance(value["generated"], dict):
        raise SavedReportError(f"{label}.generated must be an object or null")
    names = value.get("generated_files", [])
    if not isinstance(names, list) or any(not isinstance(name, str) for name in names):
        raise SavedReportError(f"{label}.generated_files must be an array of strings")


def _report(data: bytes) -> dict:
    try:
        report = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                            parse_constant=_reject_constant, parse_float=_finite_float)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise SavedReportError(f"cannot read saved report as UTF-8 JSON: {exc}") from exc
    if not isinstance(report, dict) or report.get("schema") is not None:
        raise SavedReportError("expected an unversioned TestPilot generation report")
    for name in ("status", "patch"):
        if not isinstance(report.get(name), str):
            raise SavedReportError(f"report.{name} must be text")
    _files(report.get("test_files"), "report.test_files")
    _objects(report.get("changed_functions"), "report.changed_functions")
    rounds = _objects(report.get("rounds"), "report.rounds")
    ledger = report.get("ledger")
    if not isinstance(ledger, dict):
        raise SavedReportError("report.ledger must be an object")
    _booleans(ledger, ("tokens_estimated", "cost_is_complete"), "report.ledger")
    for entry in _objects(ledger.get("entries"), "report.ledger.entries"):
        _booleans(entry, ("estimated",), "ledger entry")
    _run_layout(report.get("final"), "report.final")
    for record in rounds:
        if "contents" in record:
            _files(record["contents"], "round.contents")
        _run_layout(record.get("result"), "round.result")
    for name in ("coverage", "pytest_selection"):
        if report.get(name) is not None and not isinstance(report[name], dict):
            raise SavedReportError(f"report.{name} must be an object or null")
    return report


def _new_output(data: bytes, destination: Path) -> str | None:
    descriptor, temporary = tempfile.mkstemp(prefix=".testpilot-review-", dir=destination.parent)
    published = False
    warning = None
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # A complete file appears only if this final name is still unoccupied.
        os.link(temporary, destination)
        published = True
    finally:
        try:
            os.unlink(temporary)
        except OSError as exc:
            if not published:
                raise SavedReportError(f"review was not published; cannot remove temporary file {temporary}: {exc}") from exc
            warning = f"review was published; cannot remove temporary file {temporary}: {exc}"
    return warning


def reopen_report(report_path: str | Path, patch_path: str | Path,
                  output_path: str | Path) -> dict:
    """Create a new passive review of exact saved bytes; never execute them."""
    destination = Path(output_path)
    if destination.exists() or destination.is_symlink():
        raise SavedReportError("output already exists; choose a new HTML file")
    report_bytes = _read_file(Path(report_path), MAX_REPORT_BYTES, "report")
    patch_bytes = _read_file(Path(patch_path), MAX_PATCH_BYTES, "patch")
    report = _report(report_bytes)
    try:
        recorded = report["patch"].encode("utf-8")
        windows = report["patch"].replace("\n", "\r\n").encode("utf-8")
    except UnicodeError as exc:
        raise SavedReportError("recorded patch is not valid UTF-8 text") from exc
    if patch_bytes == recorded:
        newline_form = "recorded UTF-8"
    elif patch_bytes == windows:
        newline_form = "native Windows newline expansion"
    else:
        raise SavedReportError("selected patch bytes do not match the report's recorded patch")
    sources = {
        "report": {"bytes": len(report_bytes), "sha256": hashlib.sha256(report_bytes).hexdigest()},
        "patch": {"bytes": len(patch_bytes), "sha256": hashlib.sha256(patch_bytes).hexdigest(),
                  "newline_form": newline_form},
    }
    try:
        page = render_html_report(report_bytes, patch_bytes)
    except (KeyError, TypeError, AttributeError, ValueError, OverflowError, RecursionError) as exc:
        raise SavedReportError(f"saved report does not have the native renderable layout: {exc}") from exc
    marker = '<main class="shell">'
    if page.count(marker) != 1:
        raise SavedReportError("native renderer does not expose the expected review container")
    note = ('<section aria-labelledby="saved-pair-heading"><h2 id="saved-pair-heading">Saved artifact review</h2>'
            '<p>This page reopens the selected historical report and matching patch. '
            'No tests or model requests ran. Recorded outcomes have not been reverified.</p>'
            '<p>Source report: ' + str(sources["report"]["bytes"]) + ' bytes · SHA-256 '
            '<code>' + sources["report"]["sha256"] + '</code></p>'
            '<p>Source patch: ' + str(sources["patch"]["bytes"]) + ' bytes · SHA-256 '
            '<code>' + sources["patch"]["sha256"] + '</code></p>'
            '<p>Patch match: ' + newline_form + '. Both embedded downloads retain the selected bytes.</p></section>')
    output = page.replace(marker, marker + note, 1).encode("utf-8")
    warning = _new_output(output, destination)
    receipt = {"schema": "testpilot.saved_review/1", "output": str(destination),
               "bytes": len(output), "sha256": hashlib.sha256(output).hexdigest(),
               "sources": sources, "recorded_status": report["status"]}
    if warning is not None:
        receipt["cleanup_warning"] = warning
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reopen saved TestPilot artifacts as a new offline HTML review.")
    parser.add_argument("--report", required=True, help="saved generation report JSON")
    parser.add_argument("--patch", required=True, help="matching saved testpilot.patch")
    parser.add_argument("--out", required=True, help="new HTML file in an existing directory")
    args = parser.parse_args(argv)
    try:
        receipt = reopen_report(args.report, args.patch, args.out)
    except (OSError, SavedReportError) as exc:
        print(f"testpilot: cannot reopen saved report: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
