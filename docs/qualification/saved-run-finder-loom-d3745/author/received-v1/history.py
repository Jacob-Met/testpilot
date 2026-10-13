"""Find bounded saved generation/recheck records without executing their contents."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys

MAX_CANDIDATE_FILES = 1_000
MAX_DIRECTORY_ENTRIES = 20_000
MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
SCHEMA = "testpilot.history/1"
RECHECK_SCHEMA = "testpilot.recheck/1"
NOTICE = ("Saved records only. Reported outcomes are historical; no tests or model calls were run. "
          "Results are complete only within the selected root, depth and stated budgets; paths are not chronology.")
_GENERATION_STATUSES = {"passed", "failed", "suspected_code_bug", "no_changes", "no_tests", "budget_exhausted", "model_error"}
_MESSAGES = {
    "candidate_limit": "Candidate-file budget reached.",
    "entry_limit": "Directory-entry budget reached.",
    "total_bytes_limit": "Total report-byte budget reached.",
    "report_bytes_limit": "Report exceeds the per-file byte limit.",
    "directory_error": "Could not enumerate this directory.",
    "read_error": "Could not read a complete regular report.",
    "unsupported_schema": "Unsupported saved-report schema.",
    "invalid_json": "Not supported finite UTF-8 JSON.",
    "invalid_report": "Not a supported generation or recheck core record.",
}


class HistoryError(ValueError):
    """Options or the explicit root cannot be admitted."""


class _RecordError(ValueError):
    def __init__(self, code: str):
        self.code = code


def _require(condition: bool) -> None:
    if not condition:
        raise _RecordError("invalid_report")


def _integer(value, minimum=None) -> bool:
    return type(value) is int and (minimum is None or value >= minimum)


def _number(value) -> bool:
    return (type(value) is int and value >= 0) or (type(value) is float and math.isfinite(value) and value >= 0)


def _text_map(value) -> bool:
    return isinstance(value, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in value.items())


def _final(value, *, nullable: bool):
    if value is None:
        _require(nullable)
        return None
    _require(isinstance(value, dict))
    _require(_integer(value.get("returncode")))
    _require(all(type(value.get(k)) is bool for k in ("timed_out", "ok")))
    _require(_number(value.get("duration_s")))
    _require(all(isinstance(value.get(k), str) for k in ("output", "summary")))
    _require(all(_integer(value.get(k), 0) for k in ("passed", "failed", "errors", "skipped")))
    _require(isinstance(value.get("cases"), list))
    _require("coverage" in value and (value["coverage"] is None or isinstance(value["coverage"], dict)))
    if "junit_available" in value:
        _require(type(value["junit_available"]) is bool)
    if value.get("timeout_s") is not None:
        _require(_number(value["timeout_s"]))
    if "generated_files" in value:
        _require(isinstance(value["generated_files"], list) and all(isinstance(x, str) for x in value["generated_files"]))
    if value.get("generated") is not None:
        _require(isinstance(value["generated"], dict))
    return {**{k: value[k] for k in ("summary", "returncode", "timed_out", "passed", "failed", "errors", "skipped")},
            "junit_available": value.get("junit_available")}


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _constant(_value):
    raise ValueError("nonfinite JSON constant")


def _decode(raw: bytes) -> dict:
    try:
        document = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_pairs, parse_constant=_constant)
        pending = [document]
        while pending:
            value = pending.pop()
            if type(value) is float and not math.isfinite(value):
                raise ValueError("nonfinite decoded number")
            if isinstance(value, dict):
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)
    except (UnicodeError, ValueError, RecursionError, OverflowError) as exc:
        raise _RecordError("invalid_json") from exc
    _require(isinstance(document, dict))
    return document


def _summarize(raw: bytes, relative: str) -> dict:
    d = _decode(raw)
    schema = d.get("schema")
    if schema is not None and schema != RECHECK_SCHEMA:
        raise _RecordError("unsupported_schema")
    _require(isinstance(d.get("status"), str))
    _require(_text_map(d.get("test_files")))
    targets, context = [], None
    if schema is None:
        kind = "generation"
        required = {"status", "changed_functions", "repair_rounds_used", "max_repair_rounds", "test_files",
                    "tests_written", "final", "patch", "coverage", "ledger", "rounds", "plan", "message"}
        _require(required <= d.keys())
        _require(d["status"] in _GENERATION_STATUSES)
        _require(all(_integer(d[k], 0) for k in ("repair_rounds_used", "max_repair_rounds", "tests_written")))
        _require(all(isinstance(d[k], str) for k in ("patch", "plan", "message")))
        _require(isinstance(d["ledger"], dict) and isinstance(d["rounds"], list))
        _require(d["coverage"] is None or isinstance(d["coverage"], dict))
        if "ok" in d:
            _require(type(d["ok"]) is bool)
        _require(isinstance(d["changed_functions"], list))
        for target in d["changed_functions"]:
            _require(isinstance(target, dict))
            _require(all(isinstance(target.get(k), str) for k in ("path", "qualname", "source")))
            _require(_integer(target.get("lineno"), 1))
            _require(_integer(target.get("end_lineno"), target["lineno"]))
            _require(isinstance(target.get("changed_lines"), list) and all(_integer(x, 1) for x in target["changed_lines"]))
            targets.append({"path": target["path"], "qualname": target["qualname"]})
    else:
        kind = "recheck"
        _require(d["status"] in {"passed", "failed", "no_tests"} and type(d.get("ok")) is bool)
        _require(all(isinstance(d.get(k), str) for k in ("repo", "python", "started_at", "finished_at", "scope")))
        _require(bool(d["test_files"]) and _integer(d.get("model_calls")))
        source = d.get("source_report")
        _require(isinstance(source, dict) and all(isinstance(source.get(k), str) for k in ("path", "sha256")))
        _require("recorded_status" in source and (source["recorded_status"] is None or isinstance(source["recorded_status"], str)))
        _require(isinstance(d.get("retained_tests"), list))
        for retained in d["retained_tests"]:
            _require(isinstance(retained, dict))
            _require(all(isinstance(retained.get(k), str) for k in ("path", "sha256", "placement")))
            _require(_integer(retained.get("bytes"), 0))
        context = {k: d[k] for k in ("repo", "python", "started_at", "finished_at")}
        context["source_report"] = {k: source[k] for k in ("path", "sha256", "recorded_status")}
    _require("final" in d)
    final = _final(d["final"], nullable=kind == "generation")
    return {"path": relative, "kind": kind, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "status": d["status"], "targets": targets, "test_paths": sorted(d["test_files"]),
            "final": final, "recheck_context": context}


def scan_history(root, *, max_depth=1, statuses=(), query=None, kind=None) -> dict:
    """Return literal summaries and explicit problems within the selected scope."""
    if type(max_depth) is not int or not 0 <= max_depth <= 8:
        raise HistoryError("max_depth must be an integer from 0 through 8")
    if not isinstance(statuses, (list, tuple)) or not all(isinstance(x, str) for x in statuses):
        raise HistoryError("statuses must be a list or tuple of strings")
    if query is not None and not isinstance(query, str):
        raise HistoryError("query must be text or None")
    if kind not in (None, "generation", "recheck"):
        raise HistoryError("kind must be generation, recheck, or None")
    if not isinstance(root, (str, Path)):
        raise HistoryError("root must be a path string or Path")
    try:
        selected = Path(root).resolve(strict=True)
        if not selected.is_dir():
            raise OSError("not directory")
    except (OSError, ValueError, RuntimeError) as exc:
        raise HistoryError("root must be an existing directory") from exc
    result = {
        "schema": SCHEMA, "root": str(selected), "max_depth": max_depth,
        "filters": {"statuses": list(statuses), "query": query, "kind": kind}, "complete": True,
        "limits": {"candidate_files": MAX_CANDIDATE_FILES, "directory_entries": MAX_DIRECTORY_ENTRIES,
                   "report_bytes": MAX_REPORT_BYTES, "total_bytes": MAX_TOTAL_BYTES},
        "counts": {"entries_seen": 0, "candidate_files": 0, "bytes_read": 0, "admitted": 0, "matched": 0, "problems": 0},
        "runs": [], "problems": [], "notice": NOTICE,
    }
    counts = result["counts"]
    stopped = False
    folded = query.casefold() if query is not None else None

    def problem(relative, code):
        result["problems"].append({"path": relative, "code": code, "message": _MESSAGES[code]})

    def read_candidate(path, relative, metadata):
        nonlocal stopped
        if not stat.S_ISREG(metadata.st_mode):
            problem(relative, "read_error")
            return
        if metadata.st_size > MAX_REPORT_BYTES:
            problem(relative, "report_bytes_limit")
            return
        if metadata.st_size > MAX_TOTAL_BYTES - counts["bytes_read"]:
            problem(relative, "total_bytes_limit")
            stopped = True
            return
        try:
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
            with os.fdopen(os.open(path, flags), "rb") as stream:
                admitted = os.fstat(stream.fileno())
                if not stat.S_ISREG(admitted.st_mode):
                    problem(relative, "read_error")
                    return
                if admitted.st_size > MAX_REPORT_BYTES:
                    problem(relative, "report_bytes_limit")
                    return
                remaining = MAX_TOTAL_BYTES - counts["bytes_read"]
                if admitted.st_size > remaining:
                    problem(relative, "total_bytes_limit")
                    stopped = True
                    return
                parts, acquired = [], 0
                allowance = min(MAX_REPORT_BYTES, remaining)
                while acquired < allowance:
                    piece = stream.read(min(1024 * 1024, allowance - acquired))
                    if not piece:
                        break
                    parts.append(piece)
                    acquired += len(piece)
                    counts["bytes_read"] += len(piece)
                after = os.fstat(stream.fileno())
                if acquired != admitted.st_size or after.st_size != admitted.st_size:
                    problem(relative, "read_error")
                    return
                raw = b"".join(parts)
        except OSError:
            problem(relative, "read_error")
            return
        try:
            row = _summarize(raw, relative)
        except _RecordError as exc:
            problem(relative, exc.code)
            return
        counts["admitted"] += 1
        if statuses and row["status"] not in statuses:
            return
        if kind is not None and row["kind"] != kind:
            return
        labels = [relative, *row["test_paths"]]
        for target in row["targets"]:
            labels.extend((target["path"], target["qualname"]))
        if folded is not None and not any(folded in label.casefold() for label in labels):
            return
        result["runs"].append(row)

    def visit(directory, depth, relative):
        nonlocal stopped
        entries = []
        try:
            with os.scandir(directory) as stream:
                for entry in stream:
                    if counts["entries_seen"] >= MAX_DIRECTORY_ENTRIES:
                        problem(relative, "entry_limit")
                        stopped = True
                        return
                    counts["entries_seen"] += 1
                    entries.append(entry.name)
        except OSError:
            problem(relative, "directory_error")
            return
        for name in sorted(entries):
            if stopped:
                return
            child = directory / name
            label = name if relative == "." else relative + "/" + name
            try:
                metadata = child.lstat()
            except OSError:
                problem(label, "read_error" if name in {"report.json", "recheck.json"} else "directory_error")
                continue
            if stat.S_ISLNK(metadata.st_mode):
                continue
            if stat.S_ISDIR(metadata.st_mode):
                if depth < max_depth:
                    visit(child, depth + 1, label)
            elif name in {"report.json", "recheck.json"}:
                if counts["candidate_files"] >= MAX_CANDIDATE_FILES:
                    problem(label, "candidate_limit")
                    stopped = True
                    return
                counts["candidate_files"] += 1
                read_candidate(child, label, metadata)

    visit(selected, 0, ".")
    result["runs"].sort(key=lambda row: row["path"])
    result["problems"].sort(key=lambda row: (row["path"], row["code"]))
    counts["matched"] = len(result["runs"])
    counts["problems"] = len(result["problems"])
    result["complete"] = not result["problems"]
    return result


def render_history(result: dict) -> str:
    """Render escaped literal labels; no source or diagnostic bodies are printed."""
    encoded = lambda value: json.dumps(value, ensure_ascii=True, sort_keys=True)
    lines = ["TestPilot saved-run history", "Root: " + encoded(result["root"]),
             "Complete within selected scope: " + str(result["complete"]).lower(),
             "Counts: " + encoded(result["counts"]), "Filters: " + encoded(result["filters"])]
    for row in result["runs"]:
        lines.append(f"Run: {encoded(row['path'])} | {row['kind']} | {encoded(row['status'])} | {row['bytes']} bytes | SHA256 {row['sha256']}")
        for label, key in (("Targets", "targets"), ("Retained test paths", "test_paths"),
                           ("Recorded final", "final"), ("Recheck context", "recheck_context")):
            lines.append("  " + label + ": " + encoded(row[key]))
    for row in result["problems"]:
        lines.append(f"Problem: {encoded(row['path'])} [{row['code']}] {row['message']}")
    lines.append(result["notice"])
    return "\n".join(lines) + "\n"


def _write(stream, text: str) -> bool:
    if stream is None:
        return False
    try:
        stream.write(text)
        stream.flush()
        return True
    except Exception:
        # A failed console is not retried by interpreter shutdown. This helper
        # is private to history and does not replace other commands' writers.
        if sys.stdout is stream:
            sys.stdout = None
        if sys.stderr is stream:
            sys.stderr = None
        try:
            stream.close()
        except Exception:
            pass
        return False


def run_history_command(args) -> int:
    try:
        result = scan_history(args.root, max_depth=args.max_depth, statuses=args.status or (), query=args.query, kind=args.kind)
    except HistoryError as exc:
        _write(sys.stderr, f"testpilot: cannot scan saved runs: {exc}\n")
        return 2
    text = (json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2) + "\n") if args.json else render_history(result)
    if not _write(sys.stdout, text):
        _write(sys.stderr, "testpilot: cannot write saved-run history\n")
        return 2
    return 0 if result["complete"] else 1
