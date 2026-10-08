"""CLI: python -m testpilot run --repo PATH (--diff FILE | --git-base REF) [--script DIR] --out DIR"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .diff import DiffSourceError
from .loop import TestPilot, render_report, write_outputs
from .model import ModelError, RoutingConfig, make_client


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
    r.add_argument("--max-tokens", type=int, default=None, help="total token budget for the run")
    r.add_argument("--out", default="testpilot-out")
    a = ap.parse_args(argv)

    if a.diff == "-":
        diff_text = sys.stdin.read()
    elif a.diff:
        diff_text = Path(a.diff).read_text(encoding="utf-8")
    else:
        diff_text = subprocess.run(["git", "-C", a.repo, "diff", a.git_base, "--", "*.py"],
                                   check=True, capture_output=True, text=True).stdout
    try:
        client = make_client(a.backend, script=a.script, base_url=a.base_url)
    except ModelError as e:
        print(f"testpilot: {e}", file=sys.stderr)
        return 2
    pilot = TestPilot(client, RoutingConfig.from_env(), max_repair_rounds=a.rounds, timeout_s=a.timeout,
                      max_total_tokens=a.max_tokens)
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
