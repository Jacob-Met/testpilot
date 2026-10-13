#!/usr/bin/env python3
"""Receive TestPilot's existing regression command on the pinned fanout pair."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

INPUT_SHA = "15c25f14f6804a7b78f66b2d6a9cf1747303f09510399bd77296609c4c9ca46b"
FIXTURE_SHA = "d8f2e5aa28371c92e70d9dba449e290d5681064b79fc7b6aa86ba0889724b03a"
TOOL_MANIFEST_SHA = "e390357b1e509071bfb9125b6dd595217095140ff29a751e983486b1a8fefdb2"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_pinned(path: Path, expected: str) -> dict:
    data = path.read_bytes()
    if sha(data) != expected:
        raise ValueError(f"reviewed input changed: {path.name}")
    return json.loads(data)


def verify_tool(root: Path, manifest: dict) -> dict:
    observed = {}
    for item in manifest["source_files"]:
        path = root / item["path"]
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"source leaf is not a regular file: {item['path']}")
        raw = path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if (len(raw) != item["bytes"] or sha(raw) != item["sha256"]
                or blob != item["blob"]):
            raise ValueError(f"selected TestPilot source changed: {item['path']}")
        observed[item["path"]] = {"bytes": len(raw), "sha256": sha(raw), "blob": blob}
    return observed


def git(repo: Path, *args: str) -> bytes:
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT="0")
    return subprocess.run(
        ["git", "--no-replace-objects", "--no-lazy-fetch", "--no-optional-locks",
         "-C", str(repo), *args], env=env, check=True, capture_output=True,
        timeout=30).stdout


def worktree_snapshot(repo: Path) -> dict:
    files = {}
    for path in sorted(repo.rglob("*")):
        relative = path.relative_to(repo)
        if ".git" in relative.parts:
            continue
        if path.is_symlink():
            files[relative.as_posix()] = {"symlink": os.readlink(path)}
        elif path.is_file():
            files[relative.as_posix()] = {"sha256": sha(path.read_bytes()),
                                        "mode": path.stat().st_mode & 0o777}
    index = Path(git(repo, "rev-parse", "--git-path", "index").decode().strip())
    if not index.is_absolute():
        index = repo / index
    return {"head": git(repo, "rev-parse", "HEAD").decode().strip(),
            "status_sha256": sha(git(repo, "status", "--porcelain=v1", "-z")),
            "index_sha256": sha(index.read_bytes()) if index.exists() else None,
            "files": files}


def evaluate(report: dict, expected: dict, fixture: dict) -> dict[str, bool]:
    path = expected["generated_path"]
    generated = expected["generated_cases"]
    witness = expected["witness"]
    checks = {
        "native_verdict": report.get("schema") == "testpilot.regression/1"
            and report.get("status") == "verified_regression" and report.get("ok") is True,
        "zero_reported_model_calls": report.get("model_calls") == 0,
        "exact_retained_bytes": report.get("test_files") == fixture["test_files"]
            and report.get("retained_tests") == [{"path": path,
                "bytes": len(fixture["test_files"][path].encode()),
                "sha256": expected["retained_sha256"]}],
        "authored_input_identity": report.get("source_report", {}).get("sha256") == FIXTURE_SHA
            and report.get("source_report", {}).get("recorded_status") == "authored_receiving_fixture",
    }
    pairs = [{"generated_file": path, "nodeid": node,
              "before": "failed" if node == witness else "passed", "after": "passed"}
             for node in generated]
    comparison = report.get("comparison", {})
    checks["exact_comparison"] = comparison == {
        "comparable": True, "reason": "failed_before_passed_after", "case_pairs": pairs,
        "witnesses": [p for p in pairs if p["nodeid"] == witness],
        "unmatched_before": [], "unmatched_after": []}
    for label in ("before", "after"):
        phase = report.get(label, {})
        prediction = expected["phases"][label]
        checks[label + "_source"] = all(phase.get(k) == prediction[k] for k in
            ("commit", "tree", "source_files", "source_bytes", "snapshot_sha256"))
        native = phase.get("result", {})
        cases = native.get("cases", [])
        observed = [(c.get("nodeid"), c.get("generated_file"), c.get("outcome")) for c in cases]
        wanted = [(node, None, "passed") for node in prediction["maintained_cases"]]
        wanted += [(node, path, "failed" if label == "before" and node == witness else "passed")
                   for node in generated]
        checks[label + "_complete_case_identity_and_outcome"] = Counter(observed) == Counter(wanted)
        counts = Counter(c.get("outcome") for c in cases)
        checks[label + "_complete_native_result"] = (
            native.get("returncode") == (1 if label == "before" else 0)
            and native.get("timed_out") is False and native.get("junit_available") is True
            and native.get("ok") is (label == "after") and native.get("coverage") is None
            and native.get("generated_files") == [path]
            and all(native.get(k) == counts.get(v, 0) for k, v in
                    (("passed", "passed"), ("failed", "failed"),
                     ("errors", "error"), ("skipped", "skipped"))))
        checks[label + "_retained_counts"] = native.get("generated") == {
            "collected": 3, "passed": 2 if label == "before" else 3,
            "failed": 1 if label == "before" else 0, "error": 0, "skipped": 0}
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--testpilot-source", required=True, type=Path)
    parser.add_argument("--fanout", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    expected = load_pinned(here / "expected-inputs.json", INPUT_SHA)
    fixture_path = here / "retained-tests.json"
    fixture = load_pinned(fixture_path, FIXTURE_SHA)
    manifest = load_pinned(here / "testpilot-source.json", TOOL_MANIFEST_SHA)
    root = args.testpilot_source.resolve(strict=True)
    project = args.fanout.resolve(strict=True)
    source_before = verify_tool(root, manifest)
    retained_before = worktree_snapshot(project)
    for label in ("before", "after"):
        pin = expected["phases"][label]
        raw = git(project, "cat-file", "commit", pin["commit"])
        oid = hashlib.sha1(b"commit " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if oid != pin["commit"] or raw.splitlines()[0] != b"tree " + pin["tree"].encode():
            raise ValueError(f"{label} source identity changed")
    output = args.output.absolute()
    if output.is_symlink() or output.exists():
        raise ValueError("receiving output must be new")
    output.mkdir()
    temporary = output / "tmp"
    temporary.mkdir()
    env = dict(os.environ)
    env.pop("PYTHONOPTIMIZE", None)
    env.update(PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1",
               PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONHASHSEED="0", TMPDIR=str(temporary))
    command = [args.python, "-B", "-m", "testpilot", "regression", "--repo", str(project),
               "--report", str(fixture_path), "--before", expected["phases"]["before"]["commit"],
               "--after", expected["phases"]["after"]["commit"], "--python", args.python,
               "--timeout", "60", "--out", str(output / "command-result")]
    timed_out = False
    try:
        result = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=150)
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr, timed_out = None, exc.stdout or b"", exc.stderr or b"", True
    (output / "command.stdout").write_bytes(stdout)
    (output / "command.stderr").write_bytes(stderr)
    operation = {"command": command, "returncode": code, "timed_out": timed_out,
                 "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr)}
    (output / "operation.json").write_text(json.dumps(operation, indent=2) + "\n")
    checks = {"command_completed": code == 0 and not timed_out,
              "testpilot_source_preserved": verify_tool(root, manifest) == source_before,
              "fanout_worktree_and_index_preserved": worktree_snapshot(project) == retained_before,
              "fixture_preserved": sha(fixture_path.read_bytes()) == FIXTURE_SHA}
    report_path = output / "command-result" / "regression.json"
    if report_path.is_file():
        checks.update(evaluate(json.loads(report_path.read_bytes()), expected, fixture))
    else:
        checks["complete_command_report"] = False
    accepted = all(checks.values())
    receipt = {"schema": "testpilot-fanout-receiving/1", "accepted": accepted,
               "python": sys.version, "platform": platform.platform(),
               "tool_commit": expected["tool_commit"], "tool_tree": expected["tool_tree"],
               "fixture_sha256": FIXTURE_SHA, "expected_inputs_sha256": INPUT_SHA,
               "source_manifest_sha256": TOOL_MANIFEST_SHA, "operation": operation,
               "environment": {key: env[key] for key in ("PYTHONPATH", "PYTHONDONTWRITEBYTECODE",
                   "PYTHONNOUSERSITE", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONHASHSEED", "TMPDIR")},
               "checks": checks, "source_files": source_before,
               "report_sha256": sha(report_path.read_bytes()) if report_path.is_file() else None,
               "scope": "Actual maintained regression CLI on two published fanout trees; exact authored tests. Missing-row error-contract witness only; no model generation or performance claim."}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"accepted": accepted, "checks": checks}, sort_keys=True))
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
