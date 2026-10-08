#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Capture actual offline TestPilot fixture runs for the static browser replay."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path


def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def verify_source(root: Path, pin: dict) -> None:
    for name, expected in pin["files"].items():
        if blob_sha((root / name).read_bytes()) != expected:
            raise ValueError(f"source differs from the declared pin: {name}")


def capture(root: Path, output: Path) -> dict:
    pin = json.loads((Path(__file__).resolve().parents[1] / "source-pin.json").read_text())
    verify_source(root, pin)
    sys.path.insert(0, str(root))
    from testpilot.loop import TestPilot
    from testpilot.model import RoutingConfig, ScriptedModel
    from testpilot.sandbox import run_pytest

    # Source pinning precedes every execution. The client is constructed directly;
    # environment-selected clients, endpoints, credentials and prices are unused.
    specs = [
        {"id": "calc_clamp", "title": "Clamp boundaries", "subtitle": "A regression caught",
         "module": "calc.py", "function": "clamp", "kind": "caught",
         "witness": "from calc import clamp\n\ndef test_recorded_boundary():\n    assert clamp(5, 0, 10) == 5\n",
         "explanation": "The generated boundary tests fail on the changed implementation. The authored repair reply identifies a code bug and keeps the failing assertions. The same tests pass with the fixture's ground-truth fix."},
        {"id": "stats_median", "title": "Even-length median", "subtitle": "A regression missed",
         "module": "stats.py", "function": "median", "kind": "missed",
         "witness": "from stats import median\n\ndef test_recorded_boundary():\n    assert median([1, 2, 9, 10]) == 5.5\n",
         "explanation": "The generated tests cover odd-length inputs and pass while the even-length bug remains. An independent authored boundary witness fails on that implementation and passes with the fixture's ground-truth fix."},
    ]
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for spec in specs:
        case = root / "eval/cases" / spec["id"]
        repo = case / "repo"
        client = ScriptedModel.from_dir(case / "script")
        baseline = run_pytest(repo, timeout=10, coverage=False)
        result = TestPilot(client, RoutingConfig(), max_repair_rounds=3,
                           timeout_s=10, coverage=False).run(repo, (case / "change.diff").read_text())
        generated = run_pytest(repo, result.test_files, timeout=10, coverage=False)
        fix = {p.relative_to(case / "fix").as_posix(): p.read_text()
               for p in (case / "fix").glob("*.py")}
        fixed = run_pytest(repo, {**fix, **result.test_files}, timeout=10, coverage=False)
        witness_path = "tests/test_browser_replay_witness.py"
        witness_buggy = run_pytest(repo, {witness_path: spec["witness"]}, timeout=10, coverage=False)
        witness_fixed = run_pytest(repo, {**fix, witness_path: spec["witness"]}, timeout=10, coverage=False)
        runs = {"baseline": baseline, "generated": generated, "fixed": fixed,
                "witness_buggy": witness_buggy, "witness_fixed": witness_fixed}
        if any(r.timed_out or r.errors or r.skipped for r in runs.values()):
            raise AssertionError(f"unexpected timeout/error/skip: {spec['id']}")
        if not baseline.ok or not fixed.ok or witness_buggy.ok or not witness_fixed.ok:
            raise AssertionError(f"fixture oracle did not establish the declared boundary: {spec['id']}")
        if spec["kind"] == "caught" and (generated.ok or result.status != "suspected_code_bug"):
            raise AssertionError("clamp must retain a failing code-bug regression")
        if spec["kind"] == "missed" and (not generated.ok or result.status != "passed"):
            raise AssertionError("median fixture must retain its documented weak-test miss")
        destination = output / "cases" / spec["id"]
        destination.mkdir(parents=True)
        files = {}

        def save(name: str, content: str) -> dict:
            raw = content.encode()
            (destination / name).write_bytes(raw)
            item = {"url": f"data/cases/{spec['id']}/{name}", "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest()}
            files[name] = item
            return item

        save("change.diff", (case / "change.diff").read_text())
        save("testpilot.patch", result.patch)
        save("pipeline.json", json.dumps(result.to_dict(), indent=2) + "\n")
        save("source.py", (repo / spec["module"]).read_text())
        save("oracle.py", fix[spec["module"]])
        save("witness.py", spec["witness"])
        for name, run in runs.items():
            save(name + ".log", run.output)
        record = {**spec, "fixture": str(case.relative_to(root)),
                  "bug": json.loads((case / "case.json").read_text())["bug"],
                  "diff": (case / "change.diff").read_text(),
                  "source": (repo / spec["module"]).read_text(), "oracle": fix[spec["module"]],
                  "plan": result.plan, "status": result.status, "message": result.message,
                  "tests_written": result.tests_written, "repair_rounds": result.repair_rounds_used,
                  "scripted_calls": len(client.calls), "generated_tests": result.test_files,
                  "runs": {name: run.to_dict() for name, run in runs.items()}, "files": files}
        # A self-contained case record supports browser downloads and independent
        # checks. Its own hash is kept in the top-level record, avoiding recursion.
        save("record.json", json.dumps(record, indent=2) + "\n")
        records.append(record)
    verify_source(root, pin)
    dataset = {"schema": "testpilot.offline-replay.v1", "source": pin,
               "capture_tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "execution": {"backend": "ScriptedModel", "responses": "authored repository fixtures",
                             "live_model_calls": 0, "python": platform.python_version(),
                             "pytest": importlib.metadata.version("pytest"), "platform": platform.platform(),
                             "coverage": "disabled for this receiving capture", "source_unchanged": True},
               "cases": records}
    (output / "replays.json").write_text(json.dumps(dataset, indent=2) + "\n")
    return dataset


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, required=True,
                        help="New output directory; existing recorded evidence is never overwritten")
    args = parser.parse_args()
    dataset = capture(args.source_root.resolve(), args.output.resolve())
    print(json.dumps({"source": dataset["source"]["commit"], "execution": dataset["execution"],
                      "cases": [{"id": c["id"], "status": c["status"],
                                 "runs": {k: v["summary"] for k, v in c["runs"].items()}}
                                for c in dataset["cases"]]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
