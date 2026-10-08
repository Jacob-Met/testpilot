"""Compact independent receiver for adjacent fence compatibility."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

SOURCE, RUN, RECEIPT = (Path(value).resolve() for value in sys.argv[1:4])
RUN.mkdir()
sys.dont_write_bytecode = True
sys.path.insert(0, str(SOURCE))
from testpilot.loop import parse_test_files

TICKS = chr(96) * 3
VALUE = TICKS * 2 + "python\u2029literal"
FIRST = "from sample import target\n\ndef test_adjacent_first():\n    value = " + json.dumps(VALUE, ensure_ascii=False) + "\n    assert value.startswith(" + repr(TICKS * 2) + ")\n    assert target(1) == 3\n"
SECOND = "from sample import target\n\ndef test_adjacent_second():\n    assert target(0) == 2\n"


def pin(path):
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(),
            "bytes": len(data)}


def reply(first, second, newline="\n"):
    first, second = first.replace("\n", newline), second.replace("\n", newline)
    return (TICKS + "python path=tests/test_existing.py" + newline + first + "  " + TICKS
            + TICKS + "python path=tests/test_followup.py" + newline + second
            + TICKS + chr(96) + " \t" + newline)


before = {str(p.relative_to(SOURCE)): pin(p) for p in sorted((SOURCE / "testpilot").glob("*.py"))}
parse_controls = []
for newline in ("\n", "\r\n"):
    files, warnings = parse_test_files(reply(FIRST, SECOND, newline))
    expected = {"tests/test_existing.py": FIRST.replace("\n", newline),
                "tests/test_followup.py": SECOND.replace("\n", newline)}
    parse_controls.append({"newline": repr(newline), "actual_files": files, "warnings": warnings,
                           "exact_file_bytes": files == expected,
                           "accepted": files == expected and not warnings})

repo = RUN / "repo"
(repo / "tests").mkdir(parents=True)
original = {"sample.py": b"def target(value):\n    return value + 1\n",
            "tests/test_existing.py": b"from sample import target\n\ndef test_original():\n    assert isinstance(target(2), int)\n"}
for name, data in original.items():
    (repo / name).write_bytes(data)


def git(*args):
    return subprocess.run(["git", "-c", "commit.gpgsign=false", "-C", str(repo), *args],
                          capture_output=True, text=True, check=True, timeout=10).stdout


git("init", "-q")
git("add", "sample.py", "tests/test_existing.py")
git("-c", "user.name=Authored Receiver", "-c", "user.email=fixture@example.invalid",
    "commit", "-qm", "original")
(repo / "sample.py").write_bytes(b"def target(value):\n    return value + 2\n")
protected = {name: (repo / name).read_bytes() for name in original}
scripts = RUN / "script"
scripts.mkdir()
(scripts / "01-plan.md").write_text("Verify both changed target inputs with separate test modules.")
(scripts / "02-tests.md").write_text(reply(FIRST, SECOND), encoding="utf-8")
output = RUN / "output"
env = dict(os.environ, PYTHONPATH=str(SOURCE), PYTHONDONTWRITEBYTECODE="1",
           PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", TMPDIR=str(RUN))
command = [sys.executable, "-B", "-m", "testpilot", "run", "--repo", str(repo),
           "--git-base", "HEAD", "--backend", "scripted", "--script", str(scripts),
           "--rounds", "0", "--timeout", "10", "--python", sys.executable, "--out", str(output)]
cli = subprocess.run(command, cwd=RUN, env=env, capture_output=True, text=True, timeout=50)
(RUN / "cli.stdout.log").write_text(cli.stdout)
(RUN / "cli.stderr.log").write_text(cli.stderr)
report = json.loads((output / "report.json").read_text()) if (output / "report.json").exists() else None
protected_after_cli = all((repo / name).read_bytes() == data for name, data in protected.items())
consumer = {"command": command, "exit": cli.returncode, "status": report and report["status"],
            "tests_written": report and report["tests_written"],
            "originals_unchanged": protected_after_cli, "report": report, "patch_applies": False,
            "receiving_pytest_passed": False, "exact_delivered_bytes": False}
if cli.returncode == 0 and report["status"] == "passed":
    patch = output / "testpilot.patch"
    git("apply", "--check", str(patch))
    git("apply", str(patch))
    expected_delivered = {"tests/test_existing_testpilot.py": FIRST, "tests/test_followup.py": SECOND}
    consumer["patch_applies"] = True
    consumer["exact_delivered_bytes"] = all((repo / name).read_bytes() == content.encode()
                                           for name, content in expected_delivered.items())
    run = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                         cwd=repo, env=dict(env, PYTHONPATH=str(repo)), capture_output=True,
                         text=True, timeout=20)
    (RUN / "receiving-pytest.log").write_text(run.stdout + run.stderr)
    consumer["receiving_pytest_exit"] = run.returncode
    consumer["receiving_pytest_output"] = run.stdout
    consumer["receiving_pytest_passed"] = run.returncode == 0 and "3 passed" in run.stdout
consumer["originals_unchanged"] = protected_after_cli and all(
    (repo / name).read_bytes() == data for name, data in protected.items())
consumer["accepted"] = bool(report and cli.returncode == 0 and report["status"] == "passed"
                             and report["tests_written"] == 2 and consumer["patch_applies"]
                             and consumer["receiving_pytest_passed"] and consumer["exact_delivered_bytes"]
                             and consumer["originals_unchanged"])
assert before == {str(p.relative_to(SOURCE)): pin(p) for p in sorted((SOURCE / "testpilot").glob("*.py"))}
accepted = all(case["accepted"] for case in parse_controls) and consumer["accepted"]
result = {"source": str(SOURCE), "python": sys.version, "source_pins": before,
          "harness": pin(Path(__file__)), "parse_controls": parse_controls, "consumer": consumer,
          "source_unchanged": True, "accepted": accepted}
RECEIPT.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"receipt": str(RECEIPT), "parse_accepted": sum(c["accepted"] for c in parse_controls),
                  "parse_controls": len(parse_controls), "consumer_accepted": consumer["accepted"],
                  "cli_status": consumer["status"], "accepted": accepted}))
raise SystemExit(0 if accepted else 1)
