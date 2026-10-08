#!/usr/bin/env python3
"""Native CLI cancellation receiver, with bounded owned pytest and preserved controls."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "baseline"
OUT = ROOT / "evidence/original-cancellation"
PYTHON = "/Users/me/capturesuite-independent-checkpoint-18a24bf0c281/venv/bin/python"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wait_for_json(path, process, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            return json.loads(path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            if process.poll() is not None:
                raise RuntimeError("TestPilot exited before its real pytest fixture became ready")
            time.sleep(0.02)
    raise TimeoutError("The native pytest readiness boundary did not arrive")


def make_fixture(label, interrupt):
    folder = OUT / label
    repo = folder / "repo"
    (repo / "tests").mkdir(parents=True)
    markers = folder / "markers"
    markers.mkdir()
    (repo / "sample.py").write_text("def double(value):\n    return value * 2\n")
    test = """import json, os, time
from pathlib import Path
from sample import double

def test_existing_work():
    root = Path(MARKER_PATH)
    (root / "ready.json").write_text(json.dumps({"pid": os.getpid(), "pgid": os.getpgrp()}))
    deadline = time.monotonic() + 5
    while not (root / "release").exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    if (root / "release").exists():
        (root / "continued.json").write_text(json.dumps({"pid": os.getpid(), "work": "completed after release"}))
    assert double(2) == 4
""".replace("MARKER_PATH", repr(str(markers)))
    (repo / "tests/test_existing.py").write_text(test)
    diff = folder / "change.diff"
    diff.write_text("--- a/sample.py\n+++ b/sample.py\n@@ -1,2 +1,2 @@\n def double(value):\n-    return value\n+    return value * 2\n")
    script = folder / "script"
    script.mkdir()
    (script / "01-plan.md").write_text("Check that the changed function doubles positive input.\n")
    (script / "02-generate.md").write_text(
        "```python\n# tests/test_generated_double.py\nfrom sample import double\n\ndef test_generated_double():\n    assert double(3) == 6\n```\n")
    if not interrupt:
        (markers / "release").write_text("Ordinary completion control\n")
    return folder, repo, diff, script, markers



def process_identity(pid):
    result = subprocess.run(["ps", "-p", str(pid), "-o", "command="],
                            capture_output=True, text=True, timeout=2)
    state = subprocess.run(["ps", "-p", str(pid), "-o", "stat="],
                           capture_output=True, text=True, timeout=2)
    if result.returncode != 0 or state.stdout.strip().startswith("Z"):
        return None
    return result.stdout.strip()


def finish_owned_group(pid, identity, events):
    # A unique --rootdir in the captured command binds this PID to our fixture.
    # Never signal a reused PID or an unrelated command.
    deadline = time.monotonic() + 1
    while identity and process_identity(pid) == identity and time.monotonic() < deadline:
        time.sleep(0.02)
    if identity and process_identity(pid) == identity:
        if os.getpgid(pid) != pid:
            raise RuntimeError("Owned pytest group identity changed before cleanup")
        os.killpg(pid, signal.SIGKILL)
        events.append({"event": "receiver_cleanup_owned_pytest_group", "pgid": pid})
        deadline = time.monotonic() + 1
        while process_identity(pid) == identity and time.monotonic() < deadline:
            time.sleep(0.02)
        if process_identity(pid) == identity:
            raise RuntimeError("Owned pytest remained running after bounded cleanup")
    events.append({"event": "owned_pytest_not_running_at_exit", "pid": pid})


def run_case(label, interrupt):
    folder, repo, diff, script, markers = make_fixture(label, interrupt)
    fixture_before = {str(p.relative_to(folder)): digest(p) for root in (repo, script) for p in root.rglob("*") if p.is_file()}
    argv = [PYTHON, "-m", "testpilot", "run", "--repo", str(repo),
            "--diff", str(diff), "--backend", "scripted", "--script", str(script),
            "--python", PYTHON, "--timeout", "12", "--rounds", "0", "--out", str(folder / "output")]
    env = {**os.environ, "PYTHONPATH": str(SOURCE), "PYTHONDONTWRITEBYTECODE": "1",
           "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    events = []
    child = None
    ready = None
    identity = None
    try:
        with (folder / "cli.stdout").open("wb") as stdout, (folder / "cli.stderr").open("wb") as stderr:
            child = subprocess.Popen(argv, cwd=SOURCE, env=env, stdout=stdout, stderr=stderr,
                                     stdin=subprocess.DEVNULL, start_new_session=True)
            ready = wait_for_json(markers / "ready.json", child)
            if ready["pid"] == child.pid or ready["pgid"] != ready["pid"]:
                raise RuntimeError("Fixture did not establish the separately launched pytest session")
            identity = process_identity(ready["pid"])
            if interrupt and (not identity or "--rootdir" not in identity or "testpilot-" not in identity):
                raise RuntimeError("Cannot bind the active pytest process to this fixture")
            events.append({"event": "pytest_ready", "testpilot_pid": child.pid,
                           "command_identity": identity, **ready})
            if interrupt:
                before_signal = time.monotonic()
                child.send_signal(signal.SIGINT)  # Only this receiver's owned CLI child.
                rc = child.wait(timeout=6)
                events.append({"event": "parent_exited_after_sigint", "returncode": rc,
                               "elapsed_s": time.monotonic() - before_signal})
                (markers / "release").write_text("Released only after the interrupted CLI exited\n")
                deadline = time.monotonic() + 2
                while not (markers / "continued.json").exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                events.append({"event": "post_parent_exit_release",
                               "pytest_continued": (markers / "continued.json").exists()})
            else:
                rc = child.wait(timeout=12)
                report = json.loads((folder / "output/report.json").read_text())
                events.append({"event": "ordinary_completed", "returncode": rc,
                               "status": report["status"], "final": report["final"],
                               "model_calls": len(report["ledger"]["entries"])})
    finally:
        # The test itself has a five-second deadline. Release it even on a
        # receiving exception, then reap/stop only our own bound processes.
        if not (markers / "release").exists():
            (markers / "release").write_text("Receiver finalization release\n")
        if ready and identity:
            finish_owned_group(ready["pid"], identity, events)
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=2)
            events.append({"event": "receiver_cleanup_owned_cli_group", "pgid": child.pid})
        (folder / "lifecycle-events.json").write_text(json.dumps(events, indent=2) + "\n")
    fixture_after = {str(p.relative_to(folder)): digest(p) for root in (repo, script) for p in root.rglob("*") if p.is_file()}
    if fixture_before != fixture_after:
        raise RuntimeError("Original source or canned responses changed")
    result = {"label": label, "argv": argv, "exit_code": rc, "events": events,
              "fixture_before": fixture_before, "fixture_after": fixture_after,
              "fixture_unchanged": True,
              "continued_after_parent_exit": (markers / "continued.json").exists() if interrupt else None,
              "output_exists": (folder / "output").exists()}
    (folder / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    global SOURCE, OUT, PYTHON
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--python", default=PYTHON)
    args = parser.parse_args()
    SOURCE, OUT, PYTHON = args.source.resolve(), args.output.resolve(), args.python
    OUT.mkdir(parents=True, exist_ok=False)
    before = {str(p.relative_to(SOURCE)): digest(p) for p in SOURCE.rglob("*") if p.is_file()}
    interrupted = run_case("interrupt", True)
    ordinary = run_case("ordinary-control", False)
    after = {str(p.relative_to(SOURCE)): digest(p) for p in SOURCE.rglob("*") if p.is_file()}
    checks = {
        "interrupted_cli_failed_without_publishing_result": interrupted["exit_code"] != 0 and not interrupted["output_exists"],
        "interrupted_pytest_work_stops_before_parent_returns": not interrupted["continued_after_parent_exit"],
        "ordinary_scripted_run_passes": ordinary["exit_code"] == 0,
        "all_original_source_bytes_unchanged": before == after,
    }
    result = {"canonical_head": "f3b2135cad31852b599350564fe76dd160a6a522",
              "source_tree": "d0107a6f8b3b8cc00dadebc5f794060f275f3f5b",
              "received_source": str(SOURCE),
              "driver_sha256": digest(Path(__file__)), "python": platform.python_version(),
              "platform": platform.platform(), "selected_python": PYTHON,
              "cases": [interrupted, ordinary], "checks": checks,
              "source_before": before, "source_after": after,
              "scope": "A real SIGINT delivered only to the owned CLI child while its real pytest is active; the pytest fixture is bounded to five seconds and touches only these own fixture paths. No external provider, live task, package installation, production edit or escaped-descendant containment claim."}
    (OUT / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"checks": checks, "passed": sum(checks.values()), "total": len(checks),
                      "interrupted_returncode": interrupted["exit_code"],
                      "post_cancel_work_observed": interrupted["continued_after_parent_exit"]}))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
