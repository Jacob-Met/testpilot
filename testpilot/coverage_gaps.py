"""Inspect added-line coverage in a saved TestPilot report without rerunning it.

Path labels and source metadata are data. This module never opens recorded
source paths, executes stored code, or invokes a model, repository or tests.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_FUNCTIONS = 4096
MAX_FILES = 4096
MAX_LINE_ENTRIES = 100000
MAX_LABEL_CHARACTERS = 4096


class ReportError(ValueError):
    """The saved report cannot support the requested coverage accounting."""


def _object(value, name):
    if not isinstance(value, dict):
        raise ReportError(f"{name} must be an object")
    return value


def _label(value, name):
    if not isinstance(value, str) or not value:
        raise ReportError(f"{name} must be a nonempty string")
    if len(value) > MAX_LABEL_CHARACTERS:
        raise ReportError(f"{name} exceeds the label limit")
    return value


def _line(value, name):
    if type(value) is not int or value < 1:
        raise ReportError(f"{name} must be a positive integer")
    return value


def _lines(value, name):
    if not isinstance(value, list):
        raise ReportError(f"{name} must be an array")
    return value


def _admit(report):
    """Validate raw populations before any deduplication or associations."""
    report = _object(report, "report")
    functions = report.get("changed_functions")
    if not isinstance(functions, list):
        raise ReportError("changed_functions must be an array")
    if len(functions) > MAX_FUNCTIONS:
        raise ReportError("changed_functions exceeds the function limit")
    entries = 0
    admitted = []
    for ordinal, raw in enumerate(functions):
        raw = _object(raw, f"changed_functions[{ordinal}]")
        path = _label(raw.get("path"), "function path")
        qualname = _label(raw.get("qualname"), "function qualname")
        start = _line(raw.get("lineno"), "function lineno")
        end = _line(raw.get("end_lineno"), "function end_lineno")
        if end < start:
            raise ReportError("function end_lineno precedes lineno")
        changed = _lines(raw.get("changed_lines"), "function changed_lines")
        entries += len(changed)
        if entries > MAX_LINE_ENTRIES:
            raise ReportError("raw line entries exceed the entry limit")
        for number in changed:
            _line(number, "changed line")
            if not start <= number <= end:
                raise ReportError("changed line is outside its recorded function span")
        admitted.append((ordinal, path, qualname, start, end, changed))

    final = report.get("final")
    coverage = None
    if final is not None:
        final = _object(final, "final")
        coverage = final.get("coverage")
    files = None
    if coverage is not None:
        coverage = _object(coverage, "final.coverage")
        files = _object(coverage.get("files"), "final.coverage.files")
        if len(files) > MAX_FILES:
            raise ReportError("coverage files exceed the file limit")
        for path, raw in files.items():
            _label(path, "coverage path")
            raw = _object(raw, "coverage file")
            for kind in ("executed", "missing"):
                numbers = _lines(raw.get(kind), f"coverage {kind}")
                entries += len(numbers)
                if entries > MAX_LINE_ENTRIES:
                    raise ReportError("raw line entries exceed the entry limit")
                for number in numbers:
                    _line(number, f"coverage {kind} line")
    return admitted, files


def analyze_report(report: dict) -> dict:
    """Return unique added-line states and exact recorded function associations."""
    admitted, files = _admit(report)
    retained = files is not None
    coverage = {}
    if retained:
        for path, raw in files.items():
            executed, missing = set(raw["executed"]), set(raw["missing"])
            if executed & missing:
                raise ReportError("a retained line is both executed and missing")
            coverage[path] = (executed, missing)

    functions = []
    groups = {}
    for ordinal, path, qualname, start, end, changed in admitted:
        numbers = sorted(set(changed))
        functions.append({
            "ordinal": ordinal, "path": path, "qualname": qualname,
            "lineno": start, "end_lineno": end, "changed_lines": numbers,
        })
        for number in numbers:
            groups.setdefault(path, {}).setdefault(number, []).append(ordinal)

    counts = {name: 0 for name in ("executed", "missing", "not_represented", "unknown")}
    output_files = []
    for path in sorted(groups):
        pair = coverage.get(path)
        file_state = ("unavailable" if not retained else
                      "retained_file" if pair is not None else "not_represented")
        lines = []
        for number in sorted(groups[path]):
            state = "unknown"
            if retained:
                state = ("executed" if pair is not None and number in pair[0] else
                         "missing" if pair is not None and number in pair[1] else
                         "not_represented")
            counts[state] += 1
            lines.append({"line": number, "state": state,
                          "function_ordinals": groups[path][number]})
        output_files.append({"path": path, "coverage_state": file_state, "lines": lines})

    known = counts["executed"] + counts["missing"] if retained else None
    summary = {
        "unique_changed_lines": sum(counts.values()),
        "executed_changed_lines": counts["executed"] if retained else None,
        "missing_changed_lines": counts["missing"] if retained else None,
        "not_represented_changed_lines": counts["not_represented"] if retained else None,
        "unknown_changed_lines": counts["unknown"],
        "known_executable_changed_lines": known,
        "known_executable_changed_line_percent": (
            round(100.0 * counts["executed"] / known, 1) if known else None
        ),
    }
    result = {"schema": "testpilot.coverage-gaps.v1",
              "coverage_state": "retained" if retained else "unavailable",
              "summary": summary, "files": output_files, "functions": functions}
    result_bytes(result)  # Apply the public output bound before the API returns.
    return result


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ReportError("duplicate JSON object key")
        obj[key] = value
    return obj


def _nonfinite(value):
    raise ReportError(f"nonfinite JSON constant {value}")


def read_report(path: str | Path) -> dict:
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ReportError("report exceeds the input byte limit")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=_nonfinite)
    except ReportError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise ReportError("report must be valid UTF-8 JSON within conversion limits") from exc


def result_bytes(result: dict) -> bytes:
    try:
        payload = (json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
    except ValueError as exc:
        raise ReportError("result exceeds JSON conversion limits") from exc
    if len(payload) > MAX_OUTPUT_BYTES:
        raise ReportError("result exceeds the output byte limit")
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, help="saved TestPilot report.json")
    parser.add_argument("--output", help="new JSON output file; parent must exist")
    args = parser.parse_args(argv)
    try:
        payload = result_bytes(analyze_report(read_report(args.report)))
        if args.output is not None:
            with Path(args.output).open("xb") as stream:
                stream.write(payload)
        else:
            sys.stdout.buffer.write(payload)
            sys.stdout.buffer.flush()
    except ReportError as exc:
        print(f"coverage-gaps: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"coverage-gaps: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
