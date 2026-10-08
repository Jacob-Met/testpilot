"""Parse a unified diff and map changed lines onto Python functions (via ``ast``).

Only the *new* side of the diff matters: TestPilot writes tests for the code as
it exists after the change, so line numbers refer to the post-change file in the
working tree.
"""
from __future__ import annotations

import ast
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


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


def parse_unified_diff(text: str) -> list[FileChange]:
    """Parse ``git diff`` / ``diff -u`` output into per-file changed line sets.

    Hunk line counters are tracked so that removed lines whose content starts
    with ``-- `` are not mistaken for file headers.
    """
    files: list[FileChange] = []
    cur: FileChange | None = None
    pending_old: str | None = None
    old_left = new_left = 0
    new_ln = 0
    for line in text.splitlines():
        if cur is not None and (old_left > 0 or new_left > 0):
            if line.startswith("\\"):  # "\ No newline at end of file"
                continue
            if line.startswith("+"):
                cur.added_lines.add(new_ln)
                cur.touched_lines.add(new_ln)
                new_ln += 1
                new_left -= 1
            elif line.startswith("-"):
                # anchor a pure deletion to the surrounding new-file lines
                for anchor in (new_ln - 1, new_ln):
                    if anchor >= 1:
                        cur.touched_lines.add(anchor)
                old_left -= 1
            else:  # context line (" " prefix, or blank if whitespace was stripped)
                new_ln += 1
                new_left -= 1
                old_left -= 1
            continue
        if line.startswith("diff --git "):
            cur, pending_old = None, None
            continue
        if line.startswith("--- "):
            pending_old = _strip_path(line[4:])
            continue
        if line.startswith("+++ "):
            new_path = _strip_path(line[4:])
            cur = FileChange(
                path=new_path or pending_old or "",
                old_path=pending_old,
                is_new=pending_old is None,
                is_deleted=new_path is None,
            )
            files.append(cur)
            continue
        m = _HUNK.match(line)
        if m and cur is not None:
            old_left = int(m.group(2)) if m.group(2) is not None else 1
            new_left = int(m.group(4)) if m.group(4) is not None else 1
            new_ln = int(m.group(3))
            if new_left == 0:  # pure deletion hunk: "+N,0" means "after line N"
                new_ln += 1
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
    if parts and parts[0] in ("src", "lib"):
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _iter_functions(body, prefix: str = "", in_class: bool = False):
    """Yield (qualname, node, is_method) for top-level functions and methods.

    Nested functions are attributed to their enclosing function. Functions
    defined under ``if``/``try``/``with`` blocks at module/class level count.
    """
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield prefix + node.name, node, in_class
        elif isinstance(node, ast.ClassDef):
            yield from _iter_functions(node.body, prefix + node.name + ".", True)
        else:
            for attr in ("body", "orelse", "finalbody"):
                sub = getattr(node, attr, None)
                if isinstance(sub, list):
                    yield from _iter_functions(sub, prefix, in_class)
            for handler in getattr(node, "handlers", None) or []:
                yield from _iter_functions(handler.body, prefix, in_class)


def functions_touching(source: str, path: str, lines: set[int], added: set[int]) -> list[ChangedFunction]:
    tree = ast.parse(source, filename=path)
    src_lines = source.splitlines()
    out: list[ChangedFunction] = []
    for qualname, node, is_method in _iter_functions(tree.body):
        start = min([node.lineno] + [d.lineno for d in node.decorator_list])
        end = node.end_lineno or node.lineno
        if not any(start <= ln <= end for ln in lines):
            continue
        out.append(
            ChangedFunction(
                path=path,
                module=module_name(path),
                qualname=qualname,
                lineno=start,
                end_lineno=end,
                changed_lines=sorted(ln for ln in added if start <= ln <= end),
                source="\n".join(src_lines[start - 1 : end]),
                is_method=is_method,
            )
        )
    return out


def changed_functions(repo: str | Path, diff_text: str, include_tests: bool = False) -> list[ChangedFunction]:
    """Return the Python functions in ``repo`` touched by ``diff_text``."""
    repo = Path(repo)
    result: list[ChangedFunction] = []
    for fc in parse_unified_diff(diff_text):
        if fc.is_deleted or not fc.path.endswith(".py"):
            continue
        if not include_tests and is_test_path(fc.path):
            continue
        f = repo / fc.path
        if not f.is_file():
            continue
        result.extend(functions_touching(f.read_text(encoding="utf-8"), fc.path, fc.touched_lines, fc.added_lines))
    return result
