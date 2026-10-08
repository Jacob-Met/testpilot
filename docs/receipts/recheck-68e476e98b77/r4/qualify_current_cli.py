"""Bounded native CLI composition receiving; no live provider or historical rewrite."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = Path("/dev/shm/testpilot-recheck-r4-68e476e98b77")
SOURCE = ROOT / "source"
EV = ROOT / "evidence"
PRIOR = Path("/home/jacob/testpilot-recheck-68e476e98b77")
binding = json.loads((EV / "source-composition.json").read_text())
def sha(data):
    return hashlib.sha256(data).hexdigest()
def stamp():
    return datetime.now(timezone.utc).isoformat()
def source_pins():
    return {item["path"]: sha((SOURCE / item["path"]).read_bytes()) for item in binding["materialized_inputs"]}
def files(path):
    return {p.relative_to(path).as_posix(): sha(p.read_bytes()) for p in sorted(path.rglob("*")) if p.is_file()}
free = shutil.disk_usage(ROOT).free
preflight = {"at": stamp(), "root": str(ROOT), "uid": os.getuid(), "dev": ROOT.stat().st_dev, "free_bytes": free, "required_bytes": 128 * 1024 * 1024}
(EV / "qualification-preflight.json").write_text(json.dumps(preflight, indent=2) + "\n")
assert free >= 128 * 1024 * 1024, "unchanged 128MiB floor"
before = source_pins()
for item in binding["materialized_inputs"]:
    assert before[item["path"]] == item["sha256"]
report = PRIOR / "evidence/original-generated-run/report.json"
report_before = sha(report.read_bytes())
assert report_before == "0761bedf94965d7e8a3bfac072b5f0c3f50b854494821712c23f11f1c0fa82d2"
original = json.loads(report.read_bytes())
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(SOURCE), TMPDIR=str(ROOT / "tmp"), TESTPILOT_BACKEND="INVALID_RECHECK_MUST_NOT_CONSTRUCT_MODEL")
runs = []
def run(name, argv, timeout):
    started = stamp()
    clock = time.monotonic()
    result = subprocess.run(argv, cwd=SOURCE, env=env, capture_output=True, timeout=timeout)
    (EV / (name + ".stdout")).write_bytes(result.stdout)
    (EV / (name + ".stderr")).write_bytes(result.stderr)
    receipt = {"name": name, "argv": [str(a) for a in argv], "cwd": str(SOURCE), "started_at": started, "finished_at": stamp(), "duration_s": time.monotonic() - clock, "exit": result.returncode, "stdout_sha256": sha(result.stdout), "stderr_sha256": sha(result.stderr), "stdout": name + ".stdout", "stderr": name + ".stderr"}
    (EV / (name + "-process.json")).write_text(json.dumps(receipt, indent=2) + "\n")
    runs.append(receipt)
    return result

result = run("affected-cli-tests", [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_cli_diff_transport.py", "tests/test_recheck.py::test_cli_skips_generation_and_recheck_output_is_reusable"], 100)
assert result.returncode == 0, result.stdout + result.stderr
tests_summary = result.stdout.decode("utf-8", "replace").strip().splitlines()[-1]
fixtures = ROOT / "fixtures"
fixtures.mkdir()
cases = []
original_fixture = PRIOR / "baseline/eval/cases/calc_clamp/repo"
original_fixture_before = files(original_fixture)
for name, expected_exit, expected_generated in (
    ("buggy", 1, {"collected": 4, "error": 0, "failed": 3, "passed": 1, "skipped": 0}),
    ("fixed", 0, {"collected": 4, "error": 0, "failed": 0, "passed": 4, "skipped": 0}),
):
    checkout = fixtures / name
    shutil.copytree(original_fixture, checkout)
    if name == "fixed":
        target = checkout / "calc.py"
        target.chmod(0o644)
        target.write_bytes((PRIOR / "baseline/eval/cases/calc_clamp/fix/calc.py").read_bytes())
    checkpoint = files(checkout)
    out = EV / ("current-" + name)
    result = run("actual-recheck-" + name, [sys.executable, "-B", "-m", "testpilot", "recheck", "--repo", str(checkout), "--report", str(report), "--out", str(out), "--timeout", "10"], 20)
    assert result.returncode == expected_exit, result.stdout + result.stderr
    assert result.stderr == b""
    value = json.loads((out / "recheck.json").read_bytes())
    assert value["test_files"] == original["test_files"]
    assert value["final"]["generated"] == expected_generated
    assert value["model_calls"] == 0
    assert value["status"] == ("passed" if name == "fixed" else "failed")
    assert files(checkout) == checkpoint
    cases.append({"name": name, "exit": result.returncode, "status": value["status"], "generated": value["final"]["generated"], "model_calls": value["model_calls"], "retained_tests_exact": True, "checkout_unchanged": True, "checkout_files": checkpoint, "result_sha256": sha((out / "recheck.json").read_bytes())})
assert source_pins() == before
assert sha(report.read_bytes()) == report_before
assert files(original_fixture) == original_fixture_before
receipt = {"schema": "testpilot-cli-composition-native/4", "created_at": stamp(), "passed": True, "uid": os.getuid(), "python": sys.executable, "python_version": sys.version, "source_root": str(SOURCE), "base_commit": binding["base_commit"], "base_tree": binding["base_tree"], "product_tree": binding["product_tree"], "composition_sha256": sha((EV / "source-composition.json").read_bytes()), "source_pins": before, "source_pins_unchanged": True, "preflight": preflight, "affected_test_summary": tests_summary, "commands": runs, "actual_recheck_cases": cases, "original_report_sha256": report_before, "original_report_unchanged": True, "original_fixture_unchanged": True, "limits": "Seven incoming raw-transport methods and one existing recheck CLI case plus two actual saved-report controls. Incoming run tests intentionally use the unchanged ScriptedModel; both rechecks record zero model calls. No provider/network, broad repository suite, hosted CI, source patch application outside disposable owner fixtures or durable tmpfs claim."}
(EV / "bounded-qualification.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"passed": True, "affected_test_summary": tests_summary, "actual_rechecks": cases, "receipt": str(EV / "bounded-qualification.json"), "sha256": sha((EV / "bounded-qualification.json").read_bytes())}))
