"""Read two bounded saved reports without importing execution or provider modules."""
from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

MAX_REPORT_BYTES = 4 * 1024 * 1024
MAX_NODES = 200_000
MAX_DEPTH = 64
MAX_ITEMS = 20_000
MAX_INTEGER = 2**53 - 1
STATUSES = frozenset({"passed", "failed", "suspected_code_bug", "no_changes",
                      "no_tests", "budget_exhausted", "model_error"})


class ComparisonError(ValueError):
    """A saved input is outside the supported report contract."""


def _fail(where: str, message: str) -> None:
    raise ComparisonError(f"{where}: {message}")


def _object(value: Any, where: str) -> dict:
    if not isinstance(value, dict):
        _fail(where, "expected an object")
    return value


def _array(value: Any, where: str, limit: int = MAX_ITEMS) -> list:
    if not isinstance(value, list) or len(value) > limit:
        _fail(where, f"expected an array with at most {limit} items")
    return value


def _string(value: Any, where: str) -> str:
    if not isinstance(value, str):
        _fail(where, "expected text")
    return value


def _bool(value: Any, where: str) -> bool:
    if type(value) is not bool:
        _fail(where, "expected true or false")
    return value


def _integer(value: Any, where: str, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= MAX_INTEGER:
        _fail(where, f"expected an integer from {minimum} through {MAX_INTEGER}")
    return value


def _number(value: Any, where: str, minimum: Any = None, maximum: Any = MAX_INTEGER) -> Any:
    if type(value) not in (int, Decimal):
        _fail(where, "expected a finite number")
    if isinstance(value, Decimal) and not value.is_finite():
        _fail(where, "expected a finite number")
    if (minimum is not None and value < minimum) or value > maximum:
        _fail(where, "number outside the supported range")
    return value


def _pairs(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("JSON", "duplicate field " + repr(key[:80]))
        result[key] = value
    return result


def _decimal(token: str) -> Decimal:
    if len(token) > 128:
        _fail("JSON", "number has more than 128 characters")
    try:
        return Decimal(token)
    except InvalidOperation as exc:
        raise ComparisonError("JSON: invalid number") from exc


def _constant(token: str) -> None:
    _fail("JSON", f"non-finite constant {token} is not supported")


def _bounded(value: Any) -> None:
    remaining = MAX_NODES
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        remaining -= 1
        if remaining < 0 or depth > MAX_DEPTH:
            _fail("JSON", "report exceeds the nesting or item budget")
        if isinstance(item, dict):
            if len(item) > MAX_ITEMS:
                _fail("JSON", "object has too many fields")
            stack.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            if len(item) > MAX_ITEMS:
                _fail("JSON", "array has too many items")
            stack.extend((v, depth + 1) for v in item)
        elif type(item) is int and abs(item) > MAX_INTEGER:
            _fail("JSON", "integer exceeds the supported exact range")
        elif isinstance(item, Decimal):
            if not item.is_finite() or item.copy_abs() > MAX_INTEGER:
                _fail("JSON", "number exceeds the supported finite range")


def _text_map(value: Any, where: str, limit: int = 500) -> None:
    for key, text in _object(value, where).items():
        _string(text, where + "[" + repr(key[:80]) + "]")
    if len(value) > limit:
        _fail(where, f"at most {limit} files are supported")


def _coverage(value: Any, where: str, *, summary: bool = False) -> None:
    if value is None or value == {}:
        return
    value = _object(value, where)
    if summary:
        for key in ("total_before", "total_after", "changed_lines_before", "changed_lines_after"):
            _number(value.get(key), where + "." + key, 0, 100)
        _number(value.get("total_delta"), where + ".total_delta", -100, 100)
        _integer(value.get("changed_lines_executable"), where + ".changed_lines_executable")
    else:
        _number(value.get("percent_total"), where + ".percent_total", 0, 100)
        for name, data in _object(value.get("files"), where + ".files").items():
            data = _object(data, where + ".files[" + repr(name[:80]) + "]")
            for key in ("executed", "missing"):
                for line in _array(data.get(key), where + "." + key):
                    _integer(line, where + "." + key, 1)


def _result(value: Any, where: str) -> None:
    if value is None:
        return
    value = _object(value, where)
    _integer(value.get("returncode"), where + ".returncode", -MAX_INTEGER)
    for key in ("timed_out", "ok"):
        _bool(value.get(key), where + "." + key)
    _number(value.get("duration_s"), where + ".duration_s", 0)
    if value.get("timeout_s") is not None:
        _number(value["timeout_s"], where + ".timeout_s", 0)
    for key in ("output", "summary"):
        _string(value.get(key), where + "." + key)
    for key in ("passed", "failed", "errors", "skipped"):
        _integer(value.get(key), where + "." + key)
    if "junit_available" in value:
        _bool(value["junit_available"], where + ".junit_available")
    if "generated_files" in value:
        for name in _array(value["generated_files"], where + ".generated_files", 500):
            _string(name, where + ".generated_files")
    if value.get("generated") is not None:
        counts = _object(value["generated"], where + ".generated")
        for key in ("collected", "passed", "failed", "error", "skipped"):
            _integer(counts.get(key), where + ".generated." + key)
    for case in _array(value.get("cases"), where + ".cases"):
        case = _object(case, where + ".case")
        for key in ("nodeid", "outcome", "message"):
            _string(case.get(key), where + ".case." + key)
        if case["outcome"] not in {"passed", "failed", "error", "skipped"}:
            _fail(where + ".case.outcome", "unsupported recorded outcome")
        if case.get("generated_file") is not None:
            _string(case["generated_file"], where + ".case.generated_file")
    _coverage(value.get("coverage"), where + ".coverage")


def _validate(data: Any) -> dict:
    d = _object(data, "report")
    required = {"status", "changed_functions", "test_files", "tests_written", "repair_rounds_used", "max_repair_rounds", "final", "coverage", "ledger", "rounds", "plan", "message", "patch"}
    missing = required - d.keys()
    if missing:
        _fail("report", "missing fields: " + ", ".join(sorted(missing)))
    _string(d["status"], "report.status")
    if d["status"] not in STATUSES:
        _fail("report.status", "unsupported recorded status")
    for key in ("plan", "message", "patch"):
        _string(d.get(key), "report." + key)
    for key in ("tests_written", "repair_rounds_used", "max_repair_rounds"):
        _integer(d.get(key), "report." + key)
    if "ok" in d:
        _bool(d["ok"], "report.ok")
    _text_map(d.get("test_files"), "report.test_files")
    for target in _array(d.get("changed_functions"), "report.changed_functions", 2_000):
        target = _object(target, "target")
        for key in ("path", "qualname", "source"):
            _string(target.get(key), "target." + key)
        start = _integer(target.get("lineno"), "target.lineno", 1)
        _integer(target.get("end_lineno"), "target.end_lineno", start)
        if "module" in target:
            _string(target["module"], "target.module")
        if "is_method" in target:
            _bool(target["is_method"], "target.is_method")
        for line in _array(target.get("changed_lines"), "target.changed_lines"):
            _integer(line, "target.changed_lines", 1)
    _result(d.get("final"), "report.final")
    _coverage(d.get("coverage"), "report.coverage", summary=True)
    ledger = _object(d.get("ledger"), "report.ledger")
    _integer(ledger.get("total_tokens"), "ledger.total_tokens")
    _number(ledger.get("total_cost_usd"), "ledger.total_cost_usd")
    for key in ("cost_is_complete", "tokens_estimated"):
        _bool(ledger.get(key), "ledger." + key)
    for model, record in _object(ledger.get("by_model"), "ledger.by_model").items():
        record = _object(record, "ledger.by_model[" + repr(model[:80]) + "]")
        for key in ("calls", "prompt_tokens", "completion_tokens"):
            _integer(record.get(key), "ledger.model." + key)
        _number(record.get("cost_usd"), "ledger.model.cost_usd")
    for entry in _array(ledger.get("entries"), "ledger.entries"):
        entry = _object(entry, "ledger.entry")
        for key in ("role", "model"):
            _string(entry.get(key), "ledger.entry." + key)
        for key in ("prompt_tokens", "completion_tokens"):
            _integer(entry.get(key), "ledger.entry." + key)
        _bool(entry.get("estimated"), "ledger.entry.estimated")
        _number(entry.get("cost_usd"), "ledger.entry.cost_usd")
    for record in _array(d.get("rounds"), "report.rounds", 2_000):
        record = _object(record, "round")
        if "result" not in record:
            _fail("round.result", "missing recorded result field")
        _integer(record.get("round"), "round.round")
        _string(record.get("kind"), "round.kind")
        for key in ("files", "warnings"):
            for item in _array(record.get(key), "round." + key):
                _string(item, "round." + key)
        if record.get("contents") is not None:
            _text_map(record["contents"], "round.contents")
        _result(record.get("result"), "round.result")
    return d


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class SavedReport:
    name: str
    raw: bytes
    sha256: str
    data: Mapping[str, Any]


def parse_report(raw: bytes, name: str = "report.json") -> SavedReport:
    if not isinstance(raw, bytes) or len(raw) > MAX_REPORT_BYTES:
        _fail(name, f"expected at most {MAX_REPORT_BYTES} bytes")
    try:
        parsed = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_pairs,
                            parse_float=_decimal, parse_constant=_constant)
        _bounded(parsed)
        parsed = _validate(parsed)
    except ComparisonError:
        raise
    except (UnicodeError, ValueError, RecursionError, OverflowError) as exc:
        raise ComparisonError(f"{name}: cannot read a supported UTF-8 report ({type(exc).__name__})") from exc
    return SavedReport(name, raw, hashlib.sha256(raw).hexdigest(), _freeze(parsed))


def read_report(path: str | Path) -> SavedReport:
    path = Path(path)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            _fail(path.name, "expected a regular saved report file")
        raw = stream.read(MAX_REPORT_BYTES + 1)
    return parse_report(raw, path.name)


def target_groups(before: SavedReport, after: SavedReport) -> list[dict]:
    sides = []
    for report in (before, after):
        groups: dict[tuple[str, str], list] = {}
        for item in report.data["changed_functions"]:
            groups.setdefault((item["path"], item["qualname"]), []).append(item)
        sides.append(groups)
    return [{"path": key[0], "qualname": key[1], "before": tuple(sides[0].get(key, ())),
             "after": tuple(sides[1].get(key, ()))}
            for key in sorted(sides[0].keys() | sides[1].keys())]


def context_relation(before: SavedReport, after: SavedReport) -> str:
    groups = target_groups(before, after)
    if not groups:
        return "Neither report contains selected targets"
    if any(len(g[side]) > 1 for g in groups for side in ("before", "after")):
        return "Repeated target labels; source records are kept separately"
    if any(not g["before"] or not g["after"] for g in groups):
        return "Different selected targets"
    if all(g["before"][0] == g["after"][0] for g in groups):
        return "Same reported target records"
    if all(g["before"][0]["source"] == g["after"][0]["source"] for g in groups):
        return "Same selected source; selection metadata differs"
    return "Matching target labels; selected source differs"


def file_changes(before: SavedReport, after: SavedReport) -> list[dict]:
    left, right = before.data["test_files"], after.data["test_files"]
    result = []
    for name in sorted(left.keys() | right.keys()):
        status = ("added" if name not in left else "removed" if name not in right
                  else "unchanged" if left[name] == right[name] else "changed")
        result.append({"path": name, "status": status,
                       "before": left.get(name), "after": right.get(name)})
    return result


def write_comparison(before_path: str | Path, after_path: str | Path, output: str | Path) -> Path:
    """Admit both inputs completely, then publish one new file without overwrites."""
    from .compare_html import render_comparison
    before, after = read_report(before_path), read_report(after_path)
    if Path(output).resolve() in {Path(before_path).resolve(), Path(after_path).resolve()}:
        _fail("output", "must be a new path distinct from both input reports")
    rendered = render_comparison(before, after).encode("utf-8")
    output = Path(output)
    # The hard link publishes completed bytes while refusing an existing
    # destination, including an input alias. Both paths share the same directory.
    fd, temporary = tempfile.mkstemp(prefix=".testpilot-compare-", suffix=".html", dir=output.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return output
