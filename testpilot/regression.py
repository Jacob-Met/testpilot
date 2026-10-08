"""Execute one retained suite against two immutable local Git revisions."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

from .recheck import read_saved_tests
from .sandbox import SandboxResult, run_pytest

SCHEMA = "testpilot.regression/1"
MAX_SOURCE_FILES = 10_000
MAX_SOURCE_FILE_BYTES = 8 * 1024 * 1024
MAX_SOURCE_BYTES = 64 * 1024 * 1024
_OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_GIT_TIMEOUT = 30
_MAX_TREE_OUTPUT = 16 * 1024 * 1024


class RegressionError(ValueError):
    """The requested paired execution could not be admitted or completed."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git(repo: Path, *args: str, limit: int = 4096) -> bytes:
    # Reading original objects must not follow caller GIT_DIR/WORK_TREE,
    # replacements, optional locks, or a promisor's on-demand network fetch.
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT="0")
    try:
        result = subprocess.run(
            ["git", "--no-replace-objects", "--no-lazy-fetch", "--no-optional-locks",
             "-C", str(repo), *args], capture_output=True, env=env, timeout=_GIT_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RegressionError(f"cannot read local Git objects: {exc}") from exc
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()[-2000:]
        raise RegressionError(f"Git {args[0]} refused: {detail or result.returncode}")
    if len(result.stdout) > limit:
        raise RegressionError(f"Git {args[0]} output exceeds the admitted size limit")
    return result.stdout


def _repository(repo: str | Path) -> Path:
    try:
        project = Path(repo).expanduser().resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise RegressionError(f"cannot open repository root: {exc}") from exc
    if not project.is_dir():
        raise RegressionError("repository must be an existing directory")
    if (_git(project, "rev-parse", "--is-inside-work-tree") != b"true\n"
            or _git(project, "rev-parse", "--show-prefix") != b"\n"):
        raise RegressionError("--repo must be the root of a local Git worktree")
    return project


def _revision(repo: Path, ref: str) -> dict:
    if not isinstance(ref, str) or not ref or "\0" in ref:
        raise RegressionError("before and after must be non-empty Git revision strings")
    commit = _git(repo, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}")
    commit = commit.decode("ascii").strip()
    if not _OID.fullmatch(commit):
        raise RegressionError("Git did not return one complete commit identity")
    tree = _git(repo, "rev-parse", "--verify", "--end-of-options", commit + "^{tree}")
    tree = tree.decode("ascii").strip()
    if not _OID.fullmatch(tree):
        raise RegressionError("Git did not return one complete tree identity")
    return {"requested_ref": ref, "commit": commit, "tree": tree}


def _tree_files(repo: Path, tree: str) -> list[dict]:
    raw = _git(repo, "ls-tree", "--full-tree", "-r", "-l", "-z", tree,
               limit=_MAX_TREE_OUTPUT)
    if raw and not raw.endswith(b"\0"):
        raise RegressionError("Git tree listing was incomplete")
    records = raw[:-1].split(b"\0") if raw else []
    if len(records) > MAX_SOURCE_FILES:
        raise RegressionError(f"revision exceeds {MAX_SOURCE_FILES} source files")
    entries = []
    paths = set()
    total = 0
    for record in records:
        try:
            header, path_bytes = record.split(b"\t", 1)
            mode, kind, oid, size_raw = header.split()
            path = path_bytes.decode("utf-8")
            oid = oid.decode("ascii")
            mode = mode.decode("ascii")
        except (ValueError, UnicodeError) as exc:
            raise RegressionError("unsupported or malformed Git tree path/record") from exc
        if kind != b"blob" or mode not in {"100644", "100755"}:
            raise RegressionError(f"unsupported Git entry {path!r}: mode {mode}; "
                                  "symlinks and submodules are not materialized")
        parts = path.split("/")
        if (not path or PurePosixPath(path).is_absolute()
                or any(p in {"", ".", ".."} or p.casefold() == ".git" for p in parts)
                or "\\" in path or ":" in path or path in paths or not _OID.fullmatch(oid)):
            raise RegressionError(f"unsupported or unsafe Git path: {path!r}")
        try:
            size = int(size_raw)
        except ValueError as exc:
            raise RegressionError(f"missing Git blob size for {path!r}") from exc
        if size < 0 or size > MAX_SOURCE_FILE_BYTES:
            raise RegressionError(f"source file {path!r} exceeds {MAX_SOURCE_FILE_BYTES} bytes")
        total += size
        if total > MAX_SOURCE_BYTES:
            raise RegressionError(f"revision exceeds {MAX_SOURCE_BYTES} source bytes")
        paths.add(path)
        entries.append({"path": path, "mode": mode, "blob": oid, "bytes": size})
    return sorted(entries, key=lambda entry: entry["path"].encode("utf-8"))


def _materialize(repo: Path, entries: list[dict], destination: Path) -> None:
    destination.mkdir()
    for entry in entries:
        data = _git(repo, "cat-file", "blob", entry["blob"], limit=entry["bytes"])
        algorithm = hashlib.sha1 if len(entry["blob"]) == 40 else hashlib.sha256
        actual = algorithm(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        if len(data) != entry["bytes"] or actual != entry["blob"]:
            raise RegressionError(f"Git blob content/identity changed for {entry['path']!r}")
        target = destination.joinpath(*entry["path"].split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
        target.chmod(0o755 if entry["mode"] == "100755" else 0o644)


def _admit_tests(snapshot: Path, files: dict[str, str]) -> None:
    for path, content in files.items():
        target = snapshot / path
        for parent in target.parents:
            if parent == snapshot:
                break
            if parent.exists() and not parent.is_dir():
                raise RegressionError(f"retained test parent conflicts with committed source: {path}")
        if target.exists() and (not target.is_file() or target.read_bytes() != content.encode("utf-8")):
            raise RegressionError(f"retained test differs from committed source: {path}")


def _comparison(before: SandboxResult, after: SandboxResult, files: dict[str, str]) -> tuple[str, dict]:
    result = {"comparable": False, "reason": "", "case_pairs": [], "witnesses": [],
              "unmatched_before": [], "unmatched_after": []}
    maps = []
    for phase in (before, after):
        mapping = {}
        for case in phase.generated_cases:
            identity = (case.generated_file, case.nodeid)
            if identity in mapping:
                result["reason"] = "duplicate_generated_case_identity"
                return "inconclusive", result
            mapping[identity] = case.outcome
        maps.append(mapping)
    old, new = maps

    def identity_record(key):
        return {"generated_file": key[0], "nodeid": key[1]}

    result["unmatched_before"] = [identity_record(k) for k in sorted(old.keys() - new.keys())]
    result["unmatched_after"] = [identity_record(k) for k in sorted(new.keys() - old.keys())]
    result["case_pairs"] = [{**identity_record(k), "before": old[k], "after": new[k]}
                            for k in sorted(old.keys() & new.keys())]
    if any(p.timed_out or not p.junit_available or p.returncode not in (0, 1) or p.errors
           for p in (before, after)):
        result["reason"] = "incomplete_native_run"
    elif any({key[0] for key in mapping} != set(files) for mapping in maps):
        result["reason"] = "missing_generated_file_collection"
    elif old.keys() != new.keys():
        result["reason"] = "generated_case_identity_mismatch"
    elif any(outcome not in {"passed", "failed"} for mapping in maps for outcome in mapping.values()):
        result["reason"] = "skipped_or_unknown_generated_cases"
    else:
        result["comparable"] = True
        if not after.ok or any(outcome != "passed" for outcome in new.values()):
            result["reason"] = "after_did_not_pass"
            return "after_failed", result
        result["witnesses"] = [pair for pair in result["case_pairs"]
                               if pair["before"] == "failed" and pair["after"] == "passed"]
        if result["witnesses"]:
            result["reason"] = "failed_before_passed_after"
            return "verified_regression", result
        result["reason"] = "no_generated_failure_before"
        return "not_regression", result
    return "inconclusive", result


def check_regression(repo: str | Path, report_path: str | Path, *, before: str, after: str,
                     timeout_s: float = 60.0, python: str | None = None) -> dict:
    """Run exact saved tests on two commits, without changing the worktree/index."""
    try:
        valid_timeout = (isinstance(timeout_s, (int, float)) and not isinstance(timeout_s, bool)
                         and math.isfinite(timeout_s) and timeout_s > 0)
    except OverflowError:
        valid_timeout = False
    if not valid_timeout:
        raise RegressionError("timeout must be a finite positive number")
    if python is not None and (not isinstance(python, str) or not python):
        raise RegressionError("python must identify an executable interpreter")
    chosen = shutil.which(os.path.expanduser(python or sys.executable))
    if chosen is None:
        raise RegressionError(f"Python interpreter is unavailable: {python!r}")
    executable = str(Path(chosen).parent.resolve() / Path(chosen).name)
    started = _now()
    project = _repository(repo)
    try:
        saved = read_saved_tests(report_path)
        files = dict(saved.tests)
        phases = [_revision(project, before), _revision(project, after)]
        listings = [_tree_files(project, phase["tree"]) for phase in phases]
        for phase, entries in zip(phases, listings):
            encoded = json.dumps(entries, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
            phase.update(source_files=len(entries), source_bytes=sum(e["bytes"] for e in entries),
                         snapshot_sha256=_sha(encoded))
        with tempfile.TemporaryDirectory(prefix="testpilot-regression-") as temporary:
            snapshots = [Path(temporary) / label for label in ("before", "after")]
            # A bad after tree/test placement must refuse before the before run.
            for entries, snapshot in zip(listings, snapshots):
                _materialize(project, entries, snapshot)
                _admit_tests(snapshot, files)
            native = [run_pytest(snapshot, dict(files), timeout=timeout_s, python=executable,
                                 coverage=False, exact_files=True) for snapshot in snapshots]
        status, comparison = _comparison(native[0], native[1], files)
        for phase, result in zip(phases, native):
            phase["result"] = result.to_dict()
    except (OSError, ValueError, ET.ParseError) as exc:
        if isinstance(exc, RegressionError):
            raise
        raise RegressionError(f"cannot execute retained revision check: {exc}") from exc
    return {
        "schema": SCHEMA, "status": status, "ok": status == "verified_regression",
        "repo": str(project), "python": executable, "started_at": started, "finished_at": _now(),
        "source_report": {"path": saved.path, "sha256": saved.sha256,
                          "recorded_status": saved.source_status},
        "test_files": files,
        "retained_tests": [{"path": path, "bytes": len(content.encode("utf-8")),
                            "sha256": _sha(content.encode("utf-8"))}
                           for path, content in saved.tests],
        "before": phases[0], "after": phases[1], "comparison": comparison, "model_calls": 0,
        "scope": "Two explicit committed trees; exact retained tests; existing local pytest "
                 "sandbox and collection policy; no model, patch, checkout, or dependency install.",
    }


def _destination(repo: Path, value: str | Path) -> Path:
    target = Path(value).expanduser()
    if target.exists() or target.is_symlink():
        raise RegressionError("output must be a new directory; existing paths are not replaced")
    target = target.resolve()
    if target == repo or target.is_relative_to(repo):
        raise RegressionError("output must be outside the checked repository")
    if not target.parent.is_dir():
        raise RegressionError("output parent directory must already exist")
    return target


def render_regression(result: dict) -> str:
    """Readable observation summary; exact native evidence stays in the JSON."""
    lines = ["# TestPilot retained-suite regression check", "", f"Status: **{result['status']}**", "",
             f"Reason: {result['comparison']['reason']}", "", "| Phase | Commit | Native result |",
             "| --- | --- | --- |"]
    for label in ("before", "after"):
        phase = result[label]
        lines.append(f"| {label} | `{phase['commit']}` | {phase['result']['summary']} |")
    lines += ["", f"Matched failure-to-pass witnesses: {len(result['comparison']['witnesses'])}",
              "", "```json", json.dumps(result["comparison"]["witnesses"], indent=2)
              .replace("`", "\\u0060").replace("<", "\\u003c"), "```", "",
              "Source report SHA-256: `" + result["source_report"]["sha256"] + "`", "",
              "Model calls: 0. These are observations on two explicit revisions; they do not "
              "identify which intervening change caused a result.", "",
              "Project tests run within TestPilot's existing local execution boundary. "
              "This command adds no operating-system or network isolation.", ""]
    return "\n".join(lines)


def run_regression_command(args) -> int:
    """CLI boundary: preserve prior destinations and publish only real results."""
    created = []
    target = None
    owns_directory = False
    try:
        project = _repository(args.repo)
        target = _destination(project, args.out)
        result = check_regression(project, args.report, before=args.before, after=args.after,
                                  timeout_s=args.timeout, python=args.python)
        outputs = {"regression.json": json.dumps(result, indent=2, allow_nan=False) + "\n",
                   "regression.md": render_regression(result)}
        target.mkdir()
        owns_directory = True
        for name, text in outputs.items():
            path = target / name
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                created.append(path)
                stream.write(text)
        print(f"{result['status']}: {result['comparison']['reason']}", flush=True)
        print(f"wrote {target / 'regression.json'}, {target / 'regression.md'}", flush=True)
        return 0 if result["ok"] else 1
    except (OSError, ValueError, RuntimeError) as exc:
        # Remove only files reserved by this invocation. Never remove a prior
        # directory or a concurrent writer's entry.
        for path in created:
            try:
                path.unlink()
            except OSError:
                pass
        if owns_directory:
            try:
                target.rmdir()
            except OSError:
                pass
        if isinstance(exc, BrokenPipeError):
            try:
                sys.stdout.close()
            except OSError:
                pass
        try:
            print(f"testpilot: cannot check regression: {exc}", file=sys.stderr)
        except OSError:
            pass
        return 2
