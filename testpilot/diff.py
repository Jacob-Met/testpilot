"""Parse a unified diff and map changed lines onto Python functions (via ``ast``).

Only the *new* side of the diff matters: TestPilot writes tests for the code as
it exists after the change, so line numbers refer to the post-change file in the
working tree.
"""
from __future__ import annotations

import ast
import os
import re
import tokenize
from bisect import bisect_left, bisect_right
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_MAIL_FROM = re.compile(r"From (?:[0-9a-f]{40}|[0-9a-f]{64}) Mon Sep 17 00:00:00 2001")


@dataclass
class FileChange:
    """Changed lines for one file, in new-file line numbers."""

    path: str
    old_path: str | None
    added_lines: set[int] = field(default_factory=set)
    # added lines plus anchor lines around pure deletions
    touched_lines: set[int] = field(default_factory=set)
    is_new: bool = False
    is_deleted: bool = False


@dataclass
class ChangedFunction:
    path: str
    module: str
    qualname: str
    lineno: int
    end_lineno: int
    changed_lines: list[int]
    source: str
    is_method: bool

    @property
    def import_name(self) -> str:
        """Top-level name to import from ``module`` (class name for methods)."""
        return self.qualname.split(".")[0]

    def to_dict(self) -> dict:
        return asdict(self)


def _unquote_git_path(raw: str) -> str:
    """Decode Git's C-quoted filename bytes, including octal UTF-8 sequences."""
    escapes = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13,
               '"': 34, "\\": 92}
    decoded = bytearray()
    index = 1  # Opening double quote.
    while index < len(raw):
        char = raw[index]
        index += 1
        if char == '"':
            if index != len(raw) or 0 in decoded:
                raise ValueError("invalid Git-quoted diff path")
            return os.fsdecode(bytes(decoded))
        if char != "\\":
            decoded.extend(os.fsencode(char))
            continue
        if index >= len(raw):
            break
        escaped = raw[index]
        index += 1
        if escaped in escapes:
            decoded.append(escapes[escaped])
        elif (escaped in "0123" and index + 1 < len(raw)
              and all(digit in "01234567" for digit in raw[index:index + 2])):
            decoded.append(int(escaped + raw[index:index + 2], 8))
            index += 2
        else:
            raise ValueError("invalid escape in Git-quoted diff path")
    raise ValueError("unterminated Git-quoted diff path")


def _strip_path(raw: str) -> str | None:
    p = raw.split("\t")[0].strip()
    if p.startswith('"'):
        p = _unquote_git_path(p)
    if p == "/dev/null":
        return None
    if p.startswith(("a/", "b/")):
        p = p[2:]
    return p


class DiffFormatError(ValueError):
    """A unified diff has invalid paths, headers, ranges, or hunk records."""


def parse_unified_diff(text: str) -> list[FileChange]:
    """Parse complete git diff / diff -u hunks into changed line sets.

    Declared old/new counts must match the complete body. A damaged later hunk
    rejects the whole diff, so callers never act on a partial target selection.
    Header-looking source lines remain body records while counts are pending.
    """
    files: list[FileChange] = []
    cur: FileChange | None = None
    pending_old: str | None = None
    pending_header = False
    saw_hunk = False
    old_left = new_left = 0
    new_ln = 0

    def invalid(reason: str) -> DiffFormatError:
        return DiffFormatError(f"invalid unified diff at record {record_number}: {reason}")

    def header_path(raw: str) -> str | None:
        try:
            return _strip_path(raw)
        except ValueError as exc:
            raise invalid(str(exc)) from exc

    # Git records use LF, not Unicode separators. The token after a terminal LF
    # is not a blank context record and must not satisfy a missing hunk line.
    records = text.split("\n")
    if records[-1] == "":
        records.pop()
    mail_envelope = bool(records and _MAIL_FROM.fullmatch(records[0].removesuffix("\r")))
    record_number = 0
    for record_number, line in enumerate(records, 1):
        line = line.removesuffix("\r")  # A saved diff may use CRLF records.
        # A Git mail's terminal plain-text signature is metadata. A deleted
        # source line can be "-- "; the footer cannot fill a missing old line.
        if mail_envelope and saw_hunk and line == "-- " and record_number < len(records):
            signature = records[record_number].removesuffix("\r")
            if signature and all(
                not records[index].removesuffix("\r").startswith(("+", "-", " ", "@@", "diff --git "))
                for index in range(record_number, len(records))
            ):
                if old_left or new_left:
                    raise invalid("signature footer before a complete hunk")
                continue
        if cur is not None and (old_left > 0 or new_left > 0):
            if line == "\\ No newline at end of file":
                continue
            if line.startswith("+"):
                if new_left == 0:
                    raise invalid("addition exceeds the new range")
                cur.added_lines.add(new_ln)
                cur.touched_lines.add(new_ln)
                new_ln += 1
                new_left -= 1
            elif line.startswith("-"):
                if old_left == 0:
                    raise invalid("deletion exceeds the old range")
                # Anchor a pure deletion to the surrounding new-file lines.
                for anchor in (new_ln - 1, new_ln):
                    if anchor >= 1:
                        cur.touched_lines.add(anchor)
                old_left -= 1
            elif line.startswith(" ") or line == "":
                # Retain support for a blank context line with its space stripped.
                if old_left == 0 or new_left == 0:
                    raise invalid("context exceeds a declared range")
                new_ln += 1
                new_left -= 1
                old_left -= 1
            else:
                raise invalid("incomplete hunk or invalid body prefix")
            continue
        if line.startswith("diff --git "):
            if pending_header or (cur is not None and not saw_hunk):
                raise invalid("file headers have no complete hunk")
            cur, pending_old = None, None
            saw_hunk = False
            continue
        if line.startswith("--- "):
            if pending_header or (cur is not None and not saw_hunk):
                raise invalid("file headers have no complete hunk")
            cur = None
            pending_old = header_path(line[4:])
            pending_header = True
            saw_hunk = False
            continue
        if line.startswith("+++ "):
            if not pending_header:
                raise invalid("new file header has no old file header")
            new_path = header_path(line[4:])
            cur = FileChange(
                path=new_path or pending_old or "",
                old_path=pending_old,
                is_new=pending_old is None,
                is_deleted=new_path is None,
            )
            files.append(cur)
            pending_header = False
            continue
        if line.startswith("@@"):
            m = _HUNK.match(line)
            if m is None or cur is None:
                raise invalid("malformed hunk range or missing file headers")
            try:
                old_start, new_start = int(m.group(1)), int(m.group(3))
                old_left = int(m.group(2)) if m.group(2) is not None else 1
                new_left = int(m.group(4)) if m.group(4) is not None else 1
            except ValueError as exc:
                raise invalid("hunk range is not a supported integer") from exc
            if (old_left and old_start == 0) or (new_left and new_start == 0):
                raise invalid("nonempty hunk ranges must start at line one or later")
            if old_left == 0 and new_left == 0:
                raise invalid("hunk has no source records")
            saw_hunk = True
            new_ln = new_start
            if new_left == 0:  # "+N,0" means "after line N".
                new_ln += 1
            continue
        if line == "\\ No newline at end of file":
            if not saw_hunk:
                raise invalid("newline marker has no hunk")
            continue
        if saw_hunk and line.startswith(("+", "-", " ")):
            raise invalid("body record exceeds the declared hunk ranges")
    if old_left or new_left:
        raise invalid(f"incomplete hunk ({old_left} old and {new_left} new records missing)")
    if pending_header or (cur is not None and not saw_hunk):
        raise invalid("file headers have no complete hunk")
    return files


def is_test_path(path: str) -> bool:
    p = PurePosixPath(path)
    return (
        "tests" in p.parts
        or "test" in p.parts
        or p.name.startswith("test_")
        or p.name.endswith("_test.py")
        or p.name == "conftest.py"
    )


def module_name(path: str) -> str:
    parts = list(PurePosixPath(path).with_suffix("").parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _iter_functions(body, prefix: str = "", in_class: bool = False):
    """Yield (qualname, node, is_method) for top-level functions and methods.

    Nested functions are attributed to their enclosing function. Functions
    defined under ``if``/``try``/``with``/``match`` blocks at module/class level count.
    """
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield prefix + node.name, node, in_class
        elif isinstance(node, ast.ClassDef):
            yield from _iter_functions(node.body, prefix + node.name + ".", True)
        elif isinstance(node, ast.Match):
            for case in node.cases:
                yield from _iter_functions(case.body, prefix, in_class)
        else:
            for attr in ("body", "orelse", "finalbody"):
                sub = getattr(node, attr, None)
                if isinstance(sub, list):
                    yield from _iter_functions(sub, prefix, in_class)
            for handler in getattr(node, "handlers", None) or []:
                yield from _iter_functions(handler.body, prefix, in_class)


def functions_touching(source: str, path: str, lines: set[int], added: set[int]) -> list[ChangedFunction]:
    tree = ast.parse(source, filename=path)
    # Python physical lines use LF/CRLF/CR; other separators can be literals.
    src_lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # Reuse ordered line indexes across every function in this source file.
    touched = sorted(lines)
    additions = sorted(added)
    out: list[ChangedFunction] = []
    for qualname, node, is_method in _iter_functions(tree.body):
        start = min([node.lineno] + [d.lineno for d in node.decorator_list])
        end = node.end_lineno or node.lineno
        first = bisect_left(touched, start)
        if first == len(touched) or touched[first] > end:
            continue
        out.append(
            ChangedFunction(
                path=path,
                module=module_name(path),
                qualname=qualname,
                lineno=start,
                end_lineno=end,
                changed_lines=additions[bisect_left(additions, start):bisect_right(additions, end)],
                source="\n".join(src_lines[start - 1 : end]),
                is_method=is_method,
            )
        )
    return out


class DiffSourceError(ValueError):
    """A diff selects a source path outside the requested repository."""


def _source_path(repo: Path, raw: str) -> Path:
    """Resolve a relative diff path without admitting an outside source file."""
    relative = Path(raw)
    if relative.anchor or ".." in relative.parts:
        raise DiffSourceError(f"diff source must be repository-relative: {raw!r}")
    try:
        resolved = (repo / relative).resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise DiffSourceError(f"cannot resolve diff source: {raw!r}") from exc
    if not resolved.is_relative_to(repo):
        raise DiffSourceError(f"diff source resolves outside repository: {raw!r}")
    return resolved


def changed_functions(repo: str | Path, diff_text: str, include_tests: bool = False) -> list[ChangedFunction]:
    """Return touched Python functions, rejecting selected sources outside ``repo``.

    Paths must be relative without parent traversal. Symlinks are supported
    when their resolved destination remains inside the resolved repository.
    Source encoding follows Python's BOM and encoding-cookie rules.
    """
    repo = Path(repo).resolve()
    result: list[ChangedFunction] = []
    for fc in parse_unified_diff(diff_text):
        if fc.is_deleted or not fc.path.endswith(".py"):
            continue
        if not include_tests and is_test_path(fc.path):
            continue
        f = _source_path(repo, fc.path)
        if not f.is_file():
            continue
        with tokenize.open(f) as source_file:
            source = source_file.read()
        result.extend(functions_touching(source, fc.path, fc.touched_lines, fc.added_lines))
    return result
