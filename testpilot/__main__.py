"""CLI for test generation and native diff-target inspection."""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .diff import DiffFormatError, DiffSourceError, changed_functions, parse_unified_diff
from .loop import TestPilot, render_report, write_outputs
from .model import ModelError, RoutingConfig, make_client
from .recheck import run_recheck_command
from .regression import run_regression_command
from .targets import TargetSelectionError, resolve_targets, selection_record


def _positive_timeout(value: str) -> float:
    """Admit a run limit before reading inputs or starting any work."""
    try:
        seconds = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "timeout must be a positive finite number of seconds"
        ) from exc
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError(
            "timeout must be a positive finite number of seconds"
        )
    return seconds


def _python_executable(value: str) -> str:
    executable = shutil.which(os.path.expanduser(value))
    if executable is None:
        raise argparse.ArgumentTypeError(f"Python interpreter not found or not executable: {value}")
    # Resolve directory symlinks/.. before the sandbox changes cwd, but keep
    # the final executable symlink so a venv does not become the base Python.
    path = Path(executable)
    return str(path.parent.resolve() / path.name)


def _read_diff(args) -> str:
    """Receive raw diff bytes without imposing a source-file encoding on a hunk."""
    if args.diff == "-":
        raw = getattr(sys.stdin, "buffer", sys.stdin).read()
    elif args.diff:
        raw = Path(args.diff).read_bytes()
    else:
        # Target parsing consumes a raw source patch with fixed path prefixes.
        # User display settings and diff helpers must not replace that input.
        raw = subprocess.run(
            ["git", "-C", args.repo, "diff", "--no-ext-diff", "--no-textconv",
             "--no-color", "--src-prefix=a/", "--dst-prefix=b/",
             args.git_base, "--", "*.py"],
            check=True, capture_output=True,
        ).stdout
    if isinstance(raw, str):  # Direct callers may provide a text-only stream.
        return raw
    # Keep the former universal-newline behavior and preserve undecodable bytes.
    # Selected Python source still uses its own encoding through tokenize.open.
    text = raw.decode("utf-8", errors="surrogateescape")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _preview_targets(args) -> int:
    """Print the native selector's result without starting generation or tests."""
    try:
        diff_text = _read_diff(args)
        target_specs = getattr(args, "target", None)
        functions = (changed_functions(args.repo, diff_text) if target_specs is None
                     else resolve_targets(args.repo, diff_text, target_specs))
    except (OSError, ValueError, SyntaxError, subprocess.CalledProcessError) as exc:
        print(f"testpilot: cannot inspect targets: {exc}", file=sys.stderr)
        return 2

    if args.json:
        payload = {"changed_functions": [f.to_dict() for f in functions]}
        if target_specs is not None:
            payload["selection"] = selection_record(diff_text, target_specs)
        print(json.dumps(payload, indent=2))
    else:
        noun = "function" if len(functions) == 1 else "functions"
        qualifier = "changed" if target_specs is None else "caller-selected"
        print(f"{len(functions)} {qualifier} Python {noun} outside tests")
        if target_specs is not None:
            print(selection_record(diff_text, target_specs)["reason"])
        for function in functions:
            path = json.dumps(function.path)
            name = json.dumps(function.qualname)
            print(f"{path}:{function.lineno}-{function.end_lineno}  {name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="testpilot")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="generate, run and repair tests for a diff")
    r.add_argument("--repo", required=True)
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument("--diff", help="unified diff file ('-' for stdin)")
    g.add_argument("--git-base", help="diff the working tree against this git ref")
    r.add_argument("--backend", choices=["scripted", "tokenfactory", "openai"], default=None,
                   help="default: $TESTPILOT_BACKEND or scripted")
    r.add_argument("--script", help="dir of canned responses for the scripted backend")
    r.add_argument("--base-url", help="override OpenAI-compatible base URL")
    r.add_argument("--rounds", type=int, default=3, help="max repair rounds (default 3)")
    r.add_argument("--timeout", type=_positive_timeout, default=60.0, help="positive finite pytest timeout per run, seconds")
    r.add_argument("--no-coverage", dest="coverage", action="store_const", const=False, default=None,
                   help="run pytest without optional coverage measurement (default: automatic when installed)")
    r.add_argument("--python", type=_python_executable, metavar="EXECUTABLE",
                   help="project Python for all test runs; path or PATH command (default: this interpreter)")
    r.add_argument("--max-tokens", type=int, default=None, help="total token budget for the run")
    r.add_argument("--pytest-k", metavar="EXPR",
                   help="native pytest keyword expression for baseline, generation and every repair")
    r.add_argument("--pytest-m", metavar="EXPR",
                   help="native pytest marker expression for baseline, generation and every repair")
    r.add_argument("--out", default="testpilot-out")
    r.add_argument("--target", action="append", metavar="PATH.py::QUALNAME",
                   help="select this function explicitly; repeat for caller order, instead of automatic diff selection")

    preview = sub.add_parser("targets", help="inspect changed functions without generating or running tests")
    preview.add_argument("--repo", required=True)
    source = preview.add_mutually_exclusive_group(required=True)
    source.add_argument("--diff", help="unified diff file ('-' for stdin)")
    source.add_argument("--git-base", help="diff the working tree against this git ref")
    preview.add_argument("--json", action="store_true", help="include full native target records and source")
    preview.add_argument("--target", action="append", metavar="PATH.py::QUALNAME",
                         help="inspect this explicit function; repeat instead of automatic diff selection")
    recheck = sub.add_parser("recheck", help="rerun exact tests from a saved report without model calls")
    recheck.add_argument("--repo", required=True, help="current project checkout")
    recheck.add_argument("--report", required=True, help="saved report.json or recheck.json")
    recheck.add_argument("--out", required=True, help="new result directory outside the checked repository")
    recheck.add_argument("--timeout", type=float, default=60.0, help="pytest timeout, seconds (default 60)")
    recheck.add_argument("--python", type=_python_executable, metavar="EXECUTABLE",
                         help="project Python; path or PATH command (default: this interpreter)")
    regression = sub.add_parser("regression", help="check retained tests on two committed revisions")
    regression.add_argument("--repo", required=True, help="root of the local Git worktree")
    regression.add_argument("--report", required=True, help="saved report.json or recheck.json")
    regression.add_argument("--before", required=True, help="explicit before Git revision")
    regression.add_argument("--after", required=True, help="explicit after Git revision")
    regression.add_argument("--out", required=True, help="new result directory outside the repository")
    regression.add_argument("--timeout", type=float, default=60.0, help="pytest timeout per revision")
    regression.add_argument("--python", type=_python_executable, metavar="EXECUTABLE",
                            help="project Python for both runs (default: this interpreter)")
    a = ap.parse_args(argv)

    if a.cmd == "regression":
        return run_regression_command(a)

    if a.cmd == "recheck":
        return run_recheck_command(a)

    if a.cmd == "targets":
        return _preview_targets(a)

    diff_text = _read_diff(a)
    if a.target is not None:
        try:
            resolve_targets(a.repo, diff_text, a.target)
        except TargetSelectionError as e:
            print(f"testpilot: invalid target selection: {e}", file=sys.stderr)
            return 2
    else:
        try:
            parse_unified_diff(diff_text)
        except DiffFormatError as e:
            print(f"testpilot: invalid diff format: {e}", file=sys.stderr)
            return 2
    try:
        client = make_client(a.backend, script=a.script, base_url=a.base_url)
    except ModelError as e:
        print(f"testpilot: {e}", file=sys.stderr)
        return 2
    pilot = TestPilot(client, RoutingConfig.from_env(), max_repair_rounds=a.rounds, timeout_s=a.timeout,
                      max_total_tokens=a.max_tokens, coverage=a.coverage, python=a.python,
                      pytest_k=a.pytest_k, pytest_m=a.pytest_m)
    try:
        res = (pilot.run(a.repo, diff_text) if a.target is None
               else pilot.run(a.repo, diff_text, targets=a.target))
    except TargetSelectionError as e:
        print(f"testpilot: invalid target selection: {e}", file=sys.stderr)
        return 2
    except DiffSourceError as e:
        print(f"testpilot: invalid diff source: {e}", file=sys.stderr)
        return 2
    except DiffFormatError as e:
        print(f"testpilot: invalid diff format: {e}", file=sys.stderr)
        return 2
    paths = write_outputs(res, a.out)
    print(render_report(res).split("\n## Patch")[0])
    print(f"wrote {', '.join(str(p) for p in paths.values())}")
    return 0 if res.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
