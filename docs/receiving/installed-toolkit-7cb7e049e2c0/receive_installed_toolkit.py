"""Receive the installed composed toolkit with isolated CLI entry points and saved-patch adoption."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    source, out = args.source.resolve(strict=True), args.out.resolve()
    assert not out.exists(), "Use a new receiving directory."
    assert source not in out.parents, "Keep receiving fixtures outside the source project."
    out.mkdir(parents=True)
    project, responses, native_tmp = out / "project", out / "responses", out / "native-tmp"
    for path in (project / "selected", project / "legacy", responses, native_tmp):
        path.mkdir(parents=True)
    (out / "pytest.ini").write_text("[pytest]\ntestpaths = selected\n")
    files = {
        "calculator.py": "def double(value):\n    return value * 2\n",
        "legacy/test_legacy.py": "from calculator import double\n\ndef test_legacy():\n    assert double(10) == 20\n",
        "selected/test_existing.py": (
            "import os\nfrom calculator import double\n\n"
            "def test_existing(capfd):\n"
            "    with capfd.disabled():\n"
            "        for _ in range(256):\n"
            "            pending = memoryview(b'x' * 65536)\n"
            "            while pending:\n"
            "                pending = pending[os.write(1, pending):]\n"
            "        os.write(2, b'\\nESTATE-NATIVE-FINAL-DIAGNOSTIC\\n')\n"
            "    assert double(21) == 42\n"
        ),
    }
    for name, content in files.items():
        (project / name).write_text(content)
    originals = {name: digest(project / name) for name in files}
    diff = out / "change.diff"
    diff.write_text("--- /dev/null\n+++ b/calculator.py\n@@ -0,0 +1,2 @@\n"
                    "+def double(value):\n+    return value * 2\n")
    (responses / "01.txt").write_text("Check double with a positive example and preserve existing tests.")
    (responses / "02.txt").write_text(
        "```python path=tests/test_generated.py\nfrom calculator import double\n\n"
        "def test_double_generated():\n    assert double(3) == 7\n```\n")
    (responses / "03.txt").write_text(
        "```python path=tests/test_generated.py\nfrom calculator import double\n\n"
        "def test_double_generated():\n    assert double(3) == 6\n```\n")
    env = {**{k: v for k, v in os.environ.items() if k != "PYTHONPATH"}, "PYTHONDONTWRITEBYTECODE": "1",
           "TMPDIR": str(native_tmp)}
    commands = []

    def run(name: str, argv: list[str], cwd: Path = out) -> None:
        started = time.monotonic()
        with (out / (name + ".stdout")).open("wb") as stdout, (out / (name + ".stderr")).open("wb") as stderr:
            result = subprocess.run(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                    stdout=stdout, stderr=stderr, timeout=45)
        commands.append({"name": name, "argv": argv, "returncode": result.returncode,
                         "elapsed_s": round(time.monotonic() - started, 6)})
        assert result.returncode == 0, (name, (out / (name + ".stderr")).read_text())

    run("generate-and-repair", [sys.executable, "-I", "-B", "-m", "testpilot", "run",
        "--repo", str(project), "--diff", str(diff), "--backend", "scripted",
        "--script", str(responses), "--rounds", "1", "--timeout", "10",
        "--no-coverage", "--progress", "--out", str(out / "generated")])
    report_path = out / "generated" / "report.json"
    report = json.loads(report_path.read_text())
    assert report["status"] == "passed" and report["ok"]
    assert report["repair_rounds_used"] == 1
    assert len(report["rounds"]) == 2
    assert report["rounds"][0]["result"]["failed"] == 1
    assert report["rounds"][1]["result"]["failed"] == 0
    final = report["final"]
    assert final["passed"] == 3 and final["generated"]["passed"] == 1
    assert any(case["nodeid"] == "legacy.test_legacy::test_legacy" for case in final["cases"])
    assert final["junit_available"] and not final["timed_out"]
    progress = (out / "generate-and-repair.stderr").read_text()
    assert "[testpilot] Baseline pytest: running" in progress
    assert "[testpilot] Repairing tests: starting" in progress
    assert "Generated pytest: finished: 3 passed, 0 failed, 0 errors, 0 skipped (rc=0)" in progress
    assert "ESTATE-NATIVE-FINAL-DIAGNOSTIC" in final["output"]
    assert len(final["output"]) <= 3000
    assert {name: digest(project / name) for name in files} == originals
    assert not (project / "tests/test_generated.py").exists()

    adopted = out / "adopted-project"
    shutil.copytree(project, adopted)
    run("initialize-receiving-worktree", ["git", "init", "-q"], adopted)
    run("check-saved-patch", ["git", "apply", "--check", str(out / "generated/testpilot.patch")], adopted)
    run("apply-saved-patch", ["git", "apply", str(out / "generated/testpilot.patch")], adopted)
    for name, content in report["test_files"].items():
        assert (adopted / name).read_text() == content
    assert {name: digest(adopted / name) for name in files} == originals
    run("recheck-adopted-tests", [sys.executable, "-I", "-B", "-m", "testpilot", "recheck",
        "--repo", str(adopted), "--report", str(report_path), "--timeout", "10",
        "--out", str(out / "recheck")])
    recheck = json.loads((out / "recheck/recheck.json").read_text())
    assert recheck["status"] == "passed" and recheck["ok"]
    assert recheck["model_calls"] == 0
    assert recheck["final"]["passed"] == 3
    assert recheck["final"]["generated"]["passed"] == 1
    assert all(item["placement"] == "already_present" for item in recheck["retained_tests"])
    assert "ESTATE-NATIVE-FINAL-DIAGNOSTIC" in recheck["final"]["output"]
    assert {name: digest(adopted / name) for name in files} == originals
    receipt = {
        "status": "ACCEPT", "sandbox_sha256": digest(source / "testpilot/sandbox.py"),
        "composed_source_sha256": {str(p.relative_to(source)): digest(p) for p in sorted((source / "testpilot").glob("*.py"))},
        "unrelated_ancestor_testpaths": "selected", "legacy_case_admitted": True,
        "progress_phase_notices_received": True,
        "consumer": "actual TestPilot CLI using ScriptedModel, native pytest, saved git patch and exact-test recheck",
        "raw_noise_bytes_per_existing_test": 16 * 1024 * 1024,
        "generated_status": report["status"], "repair_rounds_used": report["repair_rounds_used"],
        "failed_generated_round": report["rounds"][0]["result"]["failed"],
        "final_cases": {key: final[key] for key in ("passed", "failed", "errors", "skipped", "junit_available")},
        "saved_output_characters": len(final["output"]), "final_diagnostic_retained": True,
        "original_project_unchanged": True, "adopted_originals_unchanged": True,
        "recheck_status": recheck["status"], "recheck_model_calls": recheck["model_calls"],
        "retained_tests": recheck["retained_tests"], "commands": commands,
        "artifacts": {str(path.relative_to(out)): {"bytes": path.stat().st_size, "sha256": digest(path)}
                      for path in (report_path, out / "generated/testpilot.patch", out / "recheck/recheck.json")},
        "limits": ["Local POSIX consumer receiving; no installed-estate or Windows claim.",
                   "The scripted backend uses fixed responses; no provider request is made."]
    }
    (out / "receiving.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
