"""Bounded R2 fixture and accepted-current-input checks; preserve all R1 evidence."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path("/home/jacob/testpilot-recheck-68e476e98b77")
SOURCE = ROOT / "candidate-r2"
OUT = ROOT / "evidence/r2"
SHA = lambda data: hashlib.sha256(data).hexdigest()
ENV = dict(os.environ, PYTHONPATH=str(SOURCE), PYTHONDONTWRITEBYTECODE="1",
           TMPDIR=str(ROOT / "tmp"), TESTPILOT_BACKEND="recheck-must-not-create-a-model")


def hash_tree(repo):
    return {p.relative_to(repo).as_posix(): SHA(p.read_bytes())
            for p in sorted(repo.rglob("*")) if p.is_file()}


def run(name, argv, expected):
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=SOURCE, env=ENV, capture_output=True, timeout=35)
    (OUT / (name + ".stdout")).write_bytes(result.stdout)
    (OUT / (name + ".stderr")).write_bytes(result.stderr)
    record = {"argv": argv, "cwd": str(SOURCE), "started_at": started,
              "finished_at": datetime.now(timezone.utc).isoformat(),
              "exit": result.returncode, "expected_exit": expected,
              "stdout_sha256": SHA(result.stdout), "stderr_sha256": SHA(result.stderr)}
    with (OUT / (name + ".command.json")).open("x") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    assert result.returncode == expected, (name, result.stdout, result.stderr)
    return record


stats = os.statvfs(ROOT)
assert stats.f_bavail * stats.f_frsize > 128 * 1024 * 1024, "128 MiB product execution floor"
composition = json.loads((OUT / "source-composition.json").read_bytes())
source_before = hash_tree(SOURCE / "testpilot")
test_before = SHA((SOURCE / "tests/test_recheck.py").read_bytes())
case = run("affected-venv-case", [
    sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
    "tests/test_recheck.py::test_nondefault_python_keeps_project_venv_identity"], 0)
assert "1 passed" in (OUT / "affected-venv-case.stdout").read_text()
old = json.loads((ROOT / "evidence/consumer-r1/receipt.json").read_bytes())
checks = []
for name in ("buggy-report", "fixed-report", "current-suite-failure"):
    before = next(item for item in old["checks"] if item["name"] == name)
    command = next(item for item in old["commands"] if item["name"] == name)
    argv = command["argv"].copy()
    destination = OUT / name
    argv[argv.index("--out") + 1] = str(destination)
    repo = Path(argv[argv.index("--repo") + 1])
    saved = Path(argv[argv.index("--report") + 1])
    assert hash_tree(repo) == before["checkout_sha256"]
    assert SHA(saved.read_bytes()) == before["report_sha256"]
    actual = run(name, argv, before["expected_exit"])
    current = json.loads((destination / "recheck.json").read_bytes())
    original = json.loads((ROOT / "evidence/consumer-r1" / name / "recheck.json").read_bytes())
    for key in ("ok", "status", "test_files", "retained_tests", "model_calls"):
        assert current[key] == original[key], (name, key)
    for key in ("generated", "passed", "failed", "errors", "skipped", "returncode", "timed_out"):
        assert current["final"][key] == original["final"][key], (name, key)
    assert current["model_calls"] == 0
    assert hash_tree(repo) == before["checkout_sha256"]
    assert SHA(saved.read_bytes()) == before["report_sha256"]
    checks.append({"name": name, "command": actual, "status": current["status"],
                   "generated": current["final"]["generated"],
                   "same_native_outcome_as_r1": True, "inputs_unchanged": True})
assert hash_tree(SOURCE / "testpilot") == source_before
assert SHA((SOURCE / "tests/test_recheck.py").read_bytes()) == test_before
report = {"created_at": datetime.now(timezone.utc).isoformat(),
          "parent": composition["parent"], "parent_tree": composition["parent_tree"],
          "source": str(SOURCE), "uid": os.getuid(), "python": sys.version,
          "runtime_source_sha256": source_before, "new_test_sha256": test_before,
          "affected_test_case": case, "current_input_consumers": checks,
          "scope": "One modified test fixture case plus three existing real-report CLI cases on exact accepted PR23 collector and PR24 HTML/loop inputs. No broad suite, new model calls, independent review or cross-version collector qualification claimed. R1 sources/results/archive remain unchanged."}
with (OUT / "bounded-qualification.json").open("x") as stream:
    json.dump(report, stream, indent=2)
    stream.write("\n")
print(json.dumps({"receipt": str(OUT / "bounded-qualification.json"),
                  "sha256": SHA((OUT / "bounded-qualification.json").read_bytes()),
                  "test_cases": 1, "real_report_controls": len(checks)}))
