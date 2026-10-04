"""Eval harness: run TestPilot on each toy repo in eval/cases and score it.

Each case directory holds:
  repo/         the repo *after* the PR (contains an injected bug)
  change.diff   the PR diff (base -> repo)
  fix/          ground-truth fixed versions of the buggy files (oracle only;
                never shown to the agent)
  script/       canned model replies for the ScriptedModel backend
  case.json     name, bug description, intended trajectory

Scoring (one sample per case, so pass@1 = solved / cases):
  bug_revealing  the agent's final tests FAIL on the buggy repo and PASS once
                 fix/ is applied (checked by the harness in the sandbox)
  solved         the agent flagged `suspected_code_bug` AND its tests are
                 bug-revealing. A green test suite on buggy code is a miss.

With the scripted backend the numbers measure the pipeline (parsing, sandbox,
repair loop, scoring), not a model. Run with --backend tokenfactory to measure
a real model; the script/ dirs are then ignored.

    python -m eval.harness [--backend scripted|tokenfactory] [--rounds 3] [--out eval/results]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from testpilot.loop import TestPilot, write_outputs  # noqa: E402
from testpilot.model import RoutingConfig, ScriptedModel, make_client  # noqa: E402
from testpilot.sandbox import run_pytest  # noqa: E402

CASES = Path(__file__).resolve().parent / "cases"


def load_cases(cases_dir: Path = CASES, only: list[str] | None = None) -> list[Path]:
    dirs = sorted(p for p in cases_dir.iterdir() if (p / "case.json").is_file())
    return [d for d in dirs if not only or d.name in only]


def evaluate_case(case: Path, *, backend: str = "scripted", rounds: int = 3, timeout: float = 10.0,
                  out_dir: Path | None = None, coverage: bool | None = None) -> dict:
    meta = json.loads((case / "case.json").read_text())
    if backend == "scripted":
        client = ScriptedModel.from_dir(case / "script")
    else:
        client = make_client(backend)
    pilot = TestPilot(client, RoutingConfig.from_env(), max_repair_rounds=rounds, timeout_s=timeout,
                      coverage=coverage)
    res = pilot.run(case / "repo", (case / "change.diff").read_text())
    if out_dir is not None:
        write_outputs(res, out_dir / case.name)

    fails_on_buggy = passes_on_fixed = None
    if res.test_files:
        # final tests vs. buggy code: reuse the loop's last run when present
        if res.final is not None:
            fails_on_buggy = not res.final["ok"]
        else:
            fails_on_buggy = not run_pytest(case / "repo", res.test_files, timeout=timeout, coverage=False).ok
        fix = {p.relative_to(case / "fix").as_posix(): p.read_text() for p in (case / "fix").rglob("*.py")}
        passes_on_fixed = run_pytest(case / "repo", {**fix, **res.test_files}, timeout=timeout, coverage=False).ok
    bug_revealing = bool(fails_on_buggy and passes_on_fixed)
    cov = res.coverage or {}
    return {
        "case": case.name,
        "bug": meta.get("bug", ""),
        "status": res.status,
        "solved": res.status == "suspected_code_bug" and bug_revealing,
        "bug_revealing": bug_revealing,
        "fails_on_buggy": fails_on_buggy,
        "passes_on_fixed": passes_on_fixed,
        "tests_written": res.tests_written,
        "rounds_used": res.repair_rounds_used,
        "max_rounds": res.max_repair_rounds,
        "model_calls": len(res.ledger["entries"]),
        "tokens": res.ledger["total_tokens"],
        "cost_usd": res.ledger["total_cost_usd"] if res.ledger["cost_is_complete"] else None,
        "changed_cov_before": cov.get("changed_lines_before"),
        "changed_cov_after": cov.get("changed_lines_after"),
        "message": res.message,
    }


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    return {
        "cases": n,
        "pass@1": round(sum(r["solved"] for r in rows) / n, 3) if n else 0.0,
        "bug_revealing_rate": round(sum(r["bug_revealing"] for r in rows) / n, 3) if n else 0.0,
        "tests_written": sum(r["tests_written"] for r in rows),
        "rounds_used": sum(r["rounds_used"] for r in rows),
        "tokens": sum(r["tokens"] for r in rows),
    }


def _fmt(v) -> str:
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "yes" if v else "no"
    return str(v)


def render_table(rows: list[dict], summary: dict, backend: str) -> str:
    cols = [("case", "case"), ("status", "agent status"), ("bug_revealing", "bug-revealing"),
            ("solved", "solved"), ("tests_written", "tests written"), ("rounds_used", "repair rounds"),
            ("model_calls", "model calls"), ("tokens", "tokens (est.)"),
            ("changed_cov_before", "changed-line cov before %"), ("changed_cov_after", "after %")]
    out = [f"Backend: {backend}", "",
           "| " + " | ".join(h for _, h in cols) + " |",
           "|" + "|".join("---" for _ in cols) + "|"]
    for r in rows:
        out.append("| " + " | ".join(_fmt(r[k]) for k, _ in cols) + " |")
    out += ["", f"pass@1 = {summary['pass@1']:.2f} ({sum(r['solved'] for r in rows)}/{summary['cases']}); "
                f"bug-revealing = {summary['bug_revealing_rate']:.2f}; tests written = {summary['tests_written']}; "
                f"repair rounds = {summary['rounds_used']}; tokens = {summary['tokens']}"]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="eval.harness")
    ap.add_argument("--backend", default="scripted", choices=["scripted", "tokenfactory", "openai"])
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--case", action="append", help="run only these case names")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "results"))
    a = ap.parse_args(argv)
    out = Path(a.out)
    rows = [evaluate_case(c, backend=a.backend, rounds=a.rounds, timeout=a.timeout, out_dir=out)
            for c in load_cases(only=a.case)]
    summary = summarize(rows)
    table = render_table(rows, summary, a.backend)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    (out / "results.md").write_text(table)
    print(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
