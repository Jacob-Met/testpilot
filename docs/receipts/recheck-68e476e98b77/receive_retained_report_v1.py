"""Receive the real saved calc_clamp report without generation or provider calls."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path("/home/jacob/testpilot-recheck-68e476e98b77")
SOURCE = ROOT / "candidate"
BASELINE = ROOT / "baseline"
OUT = ROOT / "evidence/consumer-r1"
FIXTURES = ROOT / "receiving-fixtures-r1"
SAVED = ROOT / "evidence/original-generated-run/report.json"
SHA = lambda data: hashlib.sha256(data).hexdigest()
ENV = dict(os.environ, PYTHONPATH=str(SOURCE), PYTHONDONTWRITEBYTECODE="1",
           TMPDIR=str(ROOT / "tmp"),
           TESTPILOT_BACKEND="recheck-must-not-create-a-model")
commands = []
checks = []


def now():
    return datetime.now(timezone.utc).isoformat()


def json_file(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=True)
        stream.write("\n")


def guard():
    stats = os.statvfs(ROOT)
    assert stats.f_bavail * stats.f_frsize > 128 * 1024 * 1024, "native capacity floor"


def pins(root):
    return {p.relative_to(root).as_posix(): SHA(p.read_bytes())
            for p in sorted(root.rglob("*")) if p.is_file()}


def execute(name, argv, expected, *, cwd=SOURCE, env=ENV, timeout=30):
    started, tick = now(), time.monotonic()
    try:
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=timeout)
        code, stdout, stderr, error = result.returncode, result.stdout, result.stderr, None
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr, error = None, exc.stdout or b"", exc.stderr or b"", "outer timeout"
    record = {"name": name, "argv": list(map(str, argv)), "cwd": str(cwd),
              "started_at": started, "finished_at": now(),
              "duration_s": round(time.monotonic() - tick, 6),
              "returncode": code, "expected_returncode": expected, "error": error,
              "stdout_sha256": SHA(stdout), "stderr_sha256": SHA(stderr)}
    (OUT / (name + ".stdout")).write_bytes(stdout)
    (OUT / (name + ".stderr")).write_bytes(stderr)
    json_file(OUT / (name + ".command.json"), record)
    commands.append(record)
    assert code == expected and error is None, (name, code, stdout[-5000:], stderr[-5000:])
    return stdout, stderr


def current(name, repo, expected, report=SAVED, options=(), env=ENV):
    destination = OUT / name
    before = pins(repo)
    source_report_before = SHA(report.read_bytes())
    stdout, stderr = execute(
        name, [sys.executable, "-m", "testpilot", "recheck", "--repo", str(repo),
               "--report", str(report), "--out", str(destination), "--timeout", "10", *options],
        expected, env=env,
    )
    assert pins(repo) == before, name + " altered its checkout"
    assert SHA(report.read_bytes()) == source_report_before, name + " altered its source report"
    if expected == 2:
        assert not destination.exists()
        assert b"Traceback" not in stderr
        value = None
    else:
        value = json.loads((destination / "recheck.json").read_bytes())
        assert value["model_calls"] == 0
        assert value["source_report"]["sha256"] == source_report_before
        assert value["test_files"] == json.loads(report.read_bytes())["test_files"]
        assert value["ok"] is (expected == 0)
        assert sorted(p.name for p in destination.iterdir()) == ["recheck.json", "recheck.md"]
    checks.append({"name": name, "expected_exit": expected,
                   "status": value["status"] if value else "refused",
                   "generated": value["final"]["generated"] if value else None,
                   "checkout_sha256": before, "checkout_unchanged": True,
                   "report_sha256": source_report_before, "report_unchanged": True})
    return value


def checkout(name, *, fixed=False):
    target = FIXTURES / name
    shutil.copytree(BASELINE / "eval/cases/calc_clamp/repo", target)
    if fixed:
        subject = target / "calc.py"
        subject.chmod(0o644)
        subject.write_bytes((BASELINE / "eval/cases/calc_clamp/fix/calc.py").read_bytes())
    return target


def receive():
    guard()
    OUT.mkdir()
    FIXTURES.mkdir()
    qualified = json.loads((ROOT / "evidence/qualified-focused-tests.json").read_bytes())
    product_pins = qualified["after"]
    for item in product_pins:
        assert SHA((SOURCE / item["path"]).read_bytes()) == item["sha256"], item["path"]
    baseline_pins = json.loads((ROOT / "evidence/source-readback.json").read_bytes())["files"]
    for item in baseline_pins:
        assert SHA((BASELINE / item["path"]).read_bytes()) == item["sha256"], item["path"]
    assert SHA(SAVED.read_bytes()) == "0761bedf94965d7e8a3bfac072b5f0c3f50b854494821712c23f11f1c0fa82d2"
    saved = json.loads(SAVED.read_bytes())
    assert saved["status"] == "suspected_code_bug"
    assert len(saved["ledger"]["entries"]) == 3
    saved_files = saved["test_files"]
    buggy, fixed = checkout("buggy"), checkout("fixed", fixed=True)

    # A real isolated Git checkout records the authored starting point and fix.
    for name, target in (("buggy", buggy), ("fixed", fixed)):
        execute(name + "-git-init", ["git", "init", "-q", str(target)], 0)
        execute(name + "-git-add", ["git", "-C", str(target), "add", "."], 0)
        execute(name + "-git-commit",
                ["git", "-C", str(target), "-c", "user.name=TestPilot Receiving",
                 "-c", "user.email=testpilot-receiving@invalid.local",
                 "-c", "commit.gpgsign=false", "commit", "-q", "-m", "authored " + name], 0)

    negative = current("buggy-report", buggy, 1)
    assert negative["status"] == "failed"
    assert negative["final"]["generated"]["failed"] == 3
    assert negative["final"]["generated"]["passed"] == 1
    positive = current("fixed-report", fixed, 0)
    assert positive["final"]["generated"]["passed"] == 4
    assert positive["source_report"]["recorded_status"] == "suspected_code_bug"
    assert all(item["placement"] == "temporary" for item in positive["retained_tests"])

    applied = checkout("already-applied", fixed=True)
    for rel, content in saved_files.items():
        path = applied / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))
        path.chmod(0o444)
    result = current("already-applied-readonly", applied, 0)
    assert result["final"]["generated"]["collected"] == 4
    assert all(item["placement"] == "already_present" for item in result["retained_tests"])

    conflicting = checkout("conflicting", fixed=True)
    for rel, content in saved_files.items():
        path = conflicting / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((content + "# current developer change\n").encode("utf-8"))
    current("conflicting-test", conflicting, 2)

    current("reuse-current-result", fixed, 0, OUT / "fixed-report/recheck.json")

    suite = checkout("current-suite-failure", fixed=True)
    (suite / "tests/test_current_contract.py").write_text("def test_current_contract():\n    assert False\n")
    result = current("current-suite-failure", suite, 1)
    assert result["final"]["generated"]["passed"] == 4
    assert result["final"]["failed"] == 1

    none_report = OUT / "helper-only-report.json"
    json_file(none_report, {"status": "passed", "test_files": {
        "tests/test_retained_helper.py": "def helper_only():\n    return 1\n"}})
    result = current("no-retained-case", fixed, 1, none_report)
    assert result["status"] == "no_tests"
    assert result["final"]["generated"]["passed"] == 0

    timeout_report = OUT / "timeout-report.json"
    json_file(timeout_report, {"test_files": {
        "tests/test_retained_timeout.py": "import time\ndef test_wait():\n    time.sleep(30)\n"}})
    result = current("timeout", fixed, 1, timeout_report, options=("--timeout", "0.2"))
    assert result["final"]["timed_out"]
    assert result["final"]["duration_s"] < 4

    guard()
    environment = FIXTURES / "prepared environment"
    execute("prepare-venv", [sys.executable, "-m", "venv", "--without-pip",
                             "--system-site-packages", str(environment)], 0)
    python = environment / "bin/python"
    purelib, _ = execute("venv-purelib", [str(python), "-c",
        "import sysconfig; print(sysconfig.get_paths()['purelib'])"], 0)
    module = Path(purelib.decode().strip()) / "testpilot_recheck_venv_only.py"
    module.write_text(
        "import json, os, sys\n"
        "def record():\n"
        "    with open(os.environ['RECHECK_ENV_RECEIPT'], 'w') as stream:\n"
        "        json.dump({'prefix': sys.prefix, 'executable': sys.executable}, stream)\n")
    project_env = checkout("project-environment", fixed=True)
    (project_env / "conftest.py").write_text(
        "from testpilot_recheck_venv_only import record\n"
        "def pytest_sessionstart(session):\n    record()\n")
    execution_receipt = OUT / "project-environment.json"
    environment_vars = dict(ENV, RECHECK_ENV_RECEIPT=str(execution_receipt))
    result = current("default-env-refuses-missing-dependency", project_env, 1, env=environment_vars)
    assert "ModuleNotFoundError" in result["final"]["output"]
    assert not execution_receipt.exists()
    result = current("selected-project-python", project_env, 0,
                     options=("--python", str(python)), env=environment_vars)
    assert result["final"]["generated"]["passed"] == 4
    assert result["python"] == str(python)
    actual_env = json.loads(execution_receipt.read_bytes())
    assert actual_env == {"prefix": str(environment), "executable": str(python)}

    for item in product_pins:
        assert SHA((SOURCE / item["path"]).read_bytes()) == item["sha256"], item["path"]
    for item in baseline_pins:
        assert SHA((BASELINE / item["path"]).read_bytes()) == item["sha256"], item["path"]
    assert SHA(SAVED.read_bytes()) == "0761bedf94965d7e8a3bfac072b5f0c3f50b854494821712c23f11f1c0fa82d2"
    receipt = {"created_at": now(), "uid": os.getuid(), "interpreter": sys.executable,
               "python_version": sys.version, "source_parent": qualified["parent"],
               "source_parent_tree": qualified["parent_tree"], "product_pins": product_pins,
               "retained_original_report": str(SAVED), "retained_original_report_sha256": SHA(SAVED.read_bytes()),
               "original_scripted_model_calls": 3, "new_model_calls": 0,
               "new_model_tripwire": "Every actual recheck inherits an invalid TESTPILOT_BACKEND.",
               "checks": checks, "commands": commands, "project_environment": actual_env,
               "all_source_and_original_report_pins_unchanged": True,
               "scope": "Actual maintained report against authored buggy/fixed Git checkouts and bounded receiving fixtures. Linux only; no live model/provider, patch application, full-repository suite, new collector, install or activation claim."}
    json_file(OUT / "receipt.json", receipt)
    print(json.dumps({"receipt": str(OUT / "receipt.json"), "sha256": SHA((OUT / "receipt.json").read_bytes()),
                      "recheck_controls": len(checks), "commands": len(commands),
                      "outcomes": [{"name": c["name"], "exit": c["expected_exit"], "status": c["status"]}
                                   for c in checks]}))


if __name__ == "__main__":
    try:
        receive()
    except BaseException as exc:
        if OUT.exists() and not (OUT / "failure.json").exists():
            json_file(OUT / "failure.json", {"at": now(), "error": repr(exc),
                      "completed_checks": checks, "commands": commands})
        raise
