"""CLI for test generation and native diff-target inspection."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .diff import DiffSourceError, changed_functions
from .loop import TestPilot, render_report, write_outputs
from .model import ModelError, RoutingConfig, make_client


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
        raw = subprocess.run(
            ["git", "-C", args.repo, "diff", args.git_base, "--", "*.py"],
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
        functions = changed_functions(args.repo, diff_text)
    except (OSError, ValueError, SyntaxError, subprocess.CalledProcessError) as exc:
        print(f"testpilot: cannot inspect targets: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"changed_functions": [f.to_dict() for f in functions]}, indent=2))
    else:
        noun = "function" if len(functions) == 1 else "functions"
        print(f"{len(functions)} changed Python {noun} outside tests")
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
    r.add_argument("--timeout", type=float, default=60.0, help="pytest timeout per run, seconds")
    r.add_argument("--python", type=_python_executable, metavar="EXECUTABLE",
                   help="project Python for all test runs; path or PATH command (default: this interpreter)")
    r.add_argument("--max-tokens", type=int, default=None, help="total token budget for the run")
    r.add_argument("--out", default="testpilot-out")

    preview = sub.add_parser("targets", help="inspect changed functions without generating or running tests")
    preview.add_argument("--repo", required=True)
    source = preview.add_mutually_exclusive_group(required=True)
    source.add_argument("--diff", help="unified diff file ('-' for stdin)")
    source.add_argument("--git-base", help="diff the working tree against this git ref")
    preview.add_argument("--json", action="store_true", help="include full native target records and source")
    a = ap.parse_args(argv)

    if a.cmd == "targets":
        return _preview_targets(a)

    diff_text = _read_diff(a)
    try:
        client = make_client(a.backend, script=a.script, base_url=a.base_url)
    except ModelError as e:
        print(f"testpilot: {e}", file=sys.stderr)
        return 2
    pilot = TestPilot(client, RoutingConfig.from_env(), max_repair_rounds=a.rounds, timeout_s=a.timeout,
                      max_total_tokens=a.max_tokens, python=a.python)
    try:
        res = pilot.run(a.repo, diff_text)
    except DiffSourceError as e:
        print(f"testpilot: invalid diff source: {e}", file=sys.stderr)
        return 2
    paths = write_outputs(res, a.out)
    print(render_report(res).split("\n## Patch")[0])
    print(f"wrote {', '.join(str(p) for p in paths.values())}")
    return 0 if res.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
