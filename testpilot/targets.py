"""Resolve caller-chosen Python functions without inferring dependency impact."""
from __future__ import annotations

import ast
import tokenize
from collections.abc import Sequence
from pathlib import Path

from .diff import (
    ChangedFunction,
    DiffSourceError,
    _iter_functions,
    _source_path,
    functions_touching,
    is_test_path,
    parse_unified_diff,
)

SELECTION_REASON = "Caller selected these targets; no dependency inference was performed."


class TargetSelectionError(ValueError):
    """An explicit target cannot identify one permitted current function."""


def _requested_specs(targets: Sequence[str]) -> list[str]:
    if isinstance(targets, (str, bytes)) or not isinstance(targets, Sequence):
        raise TargetSelectionError("targets must be a nonempty sequence of path.py::qualname strings")
    requested = list(targets)
    if not requested or any(not isinstance(spec, str) for spec in requested):
        raise TargetSelectionError("targets must be a nonempty sequence of path.py::qualname strings")
    return requested


def selection_record(diff_text: str, targets: Sequence[str]) -> dict:
    """Snapshot caller intent; automatic runs omit this record entirely."""
    if not isinstance(diff_text, str):
        raise TargetSelectionError("the supplied diff must be text")
    return {
        "mode": "explicit",
        "requested": _requested_specs(targets),
        "reason": SELECTION_REASON,
        "diff_text": diff_text,
    }


def resolve_targets(repo: str | Path, diff_text: str,
                    targets: Sequence[str]) -> list[ChangedFunction]:
    """Select exactly named current functions, deduplicated in caller order.

    The existing AST discovery excludes nested functions and includes methods
    and module/class control-flow definitions. A repeated qualified name in one
    source file is ambiguous, even when only one branch executes at runtime.
    No source module is imported or executed during selection.
    """
    requested = _requested_specs(targets)
    root = Path(repo).resolve()
    if not root.is_dir():
        raise TargetSelectionError(f"repository is not a directory: {str(repo)!r}")
    try:
        changes = parse_unified_diff(diff_text)
    except (TypeError, ValueError) as exc:
        raise TargetSelectionError(f"cannot parse supplied diff: {exc}") from exc

    # Resolve identities only: unrelated diff sources are never opened. A diff
    # remains context in explicit mode, and cannot add targets to the request.
    added_by_source: dict[Path, set[int]] = {}
    for change in changes:
        if change.is_deleted or not change.path.endswith(".py") or is_test_path(change.path):
            continue
        try:
            source_path = _source_path(root, change.path)
        except DiffSourceError:
            continue
        added_by_source.setdefault(source_path, set()).update(change.added_lines)

    sources: dict[Path, str] = {}
    functions_by_path: dict[str, list[ChangedFunction]] = {}
    selected: list[ChangedFunction] = []
    seen: set[tuple[Path, str, int, int]] = set()
    for spec in requested:
        raw_path, separator, qualname = spec.rpartition("::")
        if (not separator or not raw_path or not qualname
                or any(not part.isidentifier() for part in qualname.split("."))):
            raise TargetSelectionError(f"expected path.py::qualname: {spec!r}")
        path = Path(raw_path).as_posix()
        if not path.endswith(".py") or is_test_path(path):
            raise TargetSelectionError(f"target must be a Python source file outside tests: {spec!r}")
        try:
            source_path = _source_path(root, raw_path)
            resolved_path = source_path.relative_to(root).as_posix()
            if not resolved_path.endswith(".py") or is_test_path(resolved_path):
                raise TargetSelectionError(f"target resolves to a non-Python or test source: {spec!r}")
            if not source_path.is_file():
                raise TargetSelectionError(f"target source does not exist: {spec!r}")
            if source_path not in sources:
                with tokenize.open(source_path) as source_file:
                    sources[source_path] = source_file.read()
            if path not in functions_by_path:
                source = sources[source_path]
                tree = ast.parse(source, filename=path)
                starts = {node.lineno for _, node, _ in _iter_functions(tree.body)}
                functions_by_path[path] = functions_touching(
                    source, path, starts, added_by_source.get(source_path, set()))
        except TargetSelectionError:
            raise
        except (OSError, ValueError, SyntaxError, LookupError) as exc:
            raise TargetSelectionError(f"cannot inspect target {spec!r}: {exc}") from exc

        matches = [function for function in functions_by_path[path] if function.qualname == qualname]
        if not matches:
            raise TargetSelectionError(f"no selectable function matches {spec!r}")
        if len(matches) != 1:
            raise TargetSelectionError(f"ambiguous target matches {len(matches)} definitions: {spec!r}")
        function = matches[0]
        identity = (source_path, function.qualname, function.lineno, function.end_lineno)
        if identity not in seen:
            selected.append(function)
            seen.add(identity)
    return selected
