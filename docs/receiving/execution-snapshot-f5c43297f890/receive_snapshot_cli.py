"""Actual CLI witness for repository edits between baseline and generation."""
from __future__ import annotations
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

source = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()
destination.mkdir(parents=True, exist_ok=False)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def execute(command, cwd, timeout=25):
    result = subprocess.run(command, cwd=cwd, capture_output=True, timeout=timeout)
    return {"command": list(map(str, command)), "returncode": result.returncode,
            "stdout": result.stdout.decode("utf-8", "replace"),
            "stderr": result.stderr.decode("utf-8", "replace")}

def source_pins():
    return {p.relative_to(source).as_posix(): sha(p.read_bytes())
            for p in sorted((source / "testpilot").glob("*.py"))}

before_pins = source_pins()
cases = []
for label, expected, mutate in (
    ("misleading_success", 7, True),
    ("keep_initial_checkout", 2, True),
    ("unchanged_control", 2, False),
):
    case = destination / label
    case.mkdir()
    project = case / "project"
    project.mkdir()
    (project / "tests").mkdir()
    values = project / "values.py"
    values.write_text("def amount():\n    return 1\n", encoding="utf-8")
    (project / "tests/test_existing.py").write_text(
        "from values import amount\n\ndef test_existing():\n    assert amount() in (2, 7)\n",
        encoding="utf-8")
    ready, release, events = (case / name for name in ("ready", "release", "events.jsonl"))
    hook = (
        "from pathlib import Path\nimport hashlib, json, time\n\n"
        "def pytest_sessionstart(session):\n"
        f"    Path({str(ready)!r}).write_text('ready')\n"
        "    deadline = time.monotonic() + 15\n"
        f"    while not Path({str(release)!r}).exists():\n"
        "        if time.monotonic() > deadline:\n"
        "            raise RuntimeError('authored baseline barrier expired')\n"
        "        time.sleep(0.01)\n"
        "    root = Path(__file__).parent\n"
        "    raw = (root / 'values.py').read_bytes()\n"
        "    event = {'sha256': hashlib.sha256(raw).hexdigest(), 'source': raw.decode(),\n"
        "             'generated_present': (root / 'tests/test_generated.py').exists()}\n"
        f"    with Path({str(events)!r}).open('a') as stream:\n"
        "        stream.write(json.dumps(event) + '\\n')\n"
    )
    (project / "conftest.py").write_text(hook, encoding="utf-8")
    for command in (
        ["git", "init", "-q"],
        ["git", "add", "."],
        ["git", "-c", "user.name=TestPilot Snapshot Fixture", "-c",
         "user.email=testpilot-snapshot@invalid.local", "-c", "commit.gpgsign=false",
         "commit", "-qm", "before"],
    ):
        result = execute(command, project)
        assert result["returncode"] == 0, result
    initial = b"def amount():\n    return 2\n"
    later = b"def amount():\n    return 7\n"
    values.write_bytes(initial)
    captured = case / "captured"
    shutil.copytree(project, captured)
    script = case / "script"
    script.mkdir()
    (script / "01.txt").write_text("Test the selected amount function.", encoding="utf-8")
    generated = f"from values import amount\n\ndef test_generated():\n    assert amount() == {expected}\n"
    (script / "02.txt").write_text(
        "```python path=tests/test_generated.py\n" + generated + "```\n", encoding="utf-8")
    out = case / "out"
    command = [sys.executable, "-B", "-m", "testpilot", "run", "--repo", str(project),
               "--git-base", "HEAD", "--script", str(script), "--out", str(out),
               "--rounds", "0", "--timeout", "10", "--no-coverage"]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(source)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.monotonic()
    with (case / "cli-stdout.log").open("wb") as stdout, (case / "cli-stderr.log").open("wb") as stderr:
        proc = subprocess.Popen(command, cwd=source, env=env, stdout=stdout, stderr=stderr,
                                start_new_session=True)
        try:
            deadline = time.monotonic() + 20
            while not ready.exists() and proc.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            if not ready.exists():
                raise RuntimeError(f"baseline barrier was not reached: {proc.poll()}")
            if mutate:
                values.write_bytes(later)
            release.write_text("released by fixture controller", encoding="utf-8")
            rc = proc.wait(timeout=25)
        except BaseException:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
            raise
    report_raw = (out / "report.json").read_bytes()
    report = json.loads(report_raw)
    cli_events = [json.loads(line) for line in events.read_text().splitlines()]
    # Exercise the actual emitted patch on the exact checkout captured before
    # the caller's edit, independent of TestPilot's recorded final result.
    patch = out / "testpilot.patch"
    applied = execute(["git", "apply", str(patch)], captured)
    assert applied["returncode"] == 0, applied
    verified = execute([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                        "-o", "addopts=", "tests/test_generated.py"], captured)
    (case / "patch-verification.json").write_text(json.dumps(verified, indent=2) + "\n")
    row = {
        "case": label, "expected_amount": expected, "caller_edits_checkout": mutate,
        "command": command, "returncode": rc,
        "duration_seconds": round(time.monotonic() - started, 3),
        "initial_source_sha256": sha(initial), "later_source_sha256": sha(later),
        "caller_source_after_sha256": sha(values.read_bytes()),
        "caller_source_expected_preserved": values.read_bytes() == (later if mutate else initial),
        "recorded_selected_source": report["changed_functions"][0]["source"],
        "status": report["status"], "final": report["final"],
        "report_sha256": sha(report_raw), "patch_sha256": sha(patch.read_bytes()),
        "ledger_entries": len(report["ledger"]["entries"]),
        "pytest_phase_events": cli_events, "patch_applies_to_captured_checkout": True,
        "patch_pytest_on_captured_checkout_returncode": verified["returncode"],
        "oracles": {
            "baseline_and_generation_share_initial_source": (
                len(cli_events) == 2 and all(event["sha256"] == sha(initial) for event in cli_events)),
            "recorded_success_matches_captured_checkout": (
                (report["status"] == "passed") == (verified["returncode"] == 0)),
            "ordinary_caller_edit_preserved": values.read_bytes() == (later if mutate else initial),
        },
    }
    cases.append(row)
    print(json.dumps({k: row[k] for k in ("case", "status", "returncode", "oracles")}), flush=True)
receipt = {
    "schema": "hamon.testpilot_execution_snapshot.cli_receiving.v1",
    "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source": str(source),
    "source_base": subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"],
                                           text=True).strip(),
    "python": sys.version, "source_before": before_pins, "source_after": source_pins(),
    "source_unchanged": before_pins == source_pins(), "cases": cases,
    "claim_limits": [
        "Actual module CLI and native pytest in authored private fixtures; zero provider calls.",
        "Controller edits the original fixture after baseline copy and before generation.",
        "This fixture demonstrates cross-phase input inconsistency; it does not claim atomic capture during copying.",
    ],
}
raw = (json.dumps(receipt, indent=2) + "\n").encode("utf-8")
(destination / "receipt.json").write_bytes(raw)
print("RECEIPT", str(destination / "receipt.json"), len(raw), sha(raw), flush=True)
