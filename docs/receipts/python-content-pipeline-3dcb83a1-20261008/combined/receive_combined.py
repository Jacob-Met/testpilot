"""One combined public CLI -> Git -> pytest receiving fixture.

Run once with the current Python; SOURCE is the pinned sibling source directory.
All repositories and model replies are authored, local, and created by this run.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source"
RUN = ROOT / "combined-consumer"
RUN.mkdir(exist_ok=False)
REPO = RUN / "repo"
REPO.mkdir()
OUT = RUN / "output"
SCRIPTS = RUN / "script"
SCRIPTS.mkdir()
PYTHON = sys.executable
FENCE = chr(96) * 3
VALUE = "answer" + FENCE + "python\u2029tail"
SOURCE_BEFORE = 'def context():\n    return "left\u2028right"\n\ndef target():\n    return "old"\n'
SOURCE_AFTER = SOURCE_BEFORE.replace('"old"', json.dumps(VALUE, ensure_ascii=False))
EXISTING = ('from sample import context\n\n'
            'def test_existing_context():\n    assert context() == "left\\u2028right"\n')
GENERATED = ('from sample import target\n\n'
             'def test_exact_literal():\n'
             f'    assert target() == {json.dumps(VALUE, ensure_ascii=False)}\n\n'
             'def test_literal_length():\n'
             f'    assert len(target()) == {len(VALUE)}\n')
compile(SOURCE_AFTER, "sample.py", "exec")
compile(GENERATED, "authored-generated.py", "exec")
(REPO / "sample.py").write_text(SOURCE_BEFORE, encoding="utf-8")
(REPO / "tests").mkdir()
(REPO / "tests/test_existing.py").write_text(EXISTING, encoding="utf-8")
git_base = ["git", "-c", "core.autocrlf=false", "-c", "core.hooksPath=/dev/null",
            "-c", "commit.gpgsign=false", "-C", str(REPO)]
for args in (["init", "-q"], ["add", "."],
             ["-c", "user.name=Authored Receiving Fixture",
              "-c", "user.email=fixture@example.invalid", "commit", "-qm", "authored baseline"]):
    subprocess.run(git_base + args, check=True, capture_output=True)
(REPO / "sample.py").write_text(SOURCE_AFTER, encoding="utf-8")
diff = subprocess.run(git_base + ["diff", "HEAD", "--", "*.py"],
                      check=True, capture_output=True).stdout
(RUN / "actual.diff").write_bytes(diff)
(SCRIPTS / "01-plan.md").write_text(
    "Test the exact new literal and its length; retain the original context test.\n",
    encoding="utf-8")
(SCRIPTS / "02-tests.md").write_text(
    FENCE + "python path=tests/test_existing.py\n" + GENERATED + FENCE + "\n",
    encoding="utf-8")
env = dict(os.environ, PYTHONPATH=str(SOURCE), PYTHONDONTWRITEBYTECODE="1",
           TESTPILOT_PLANNER_MODEL="authored-plan", TESTPILOT_EDITOR_MODEL="authored-edit",
           TESTPILOT_PRICES="{}")
command = [PYTHON, "-m", "testpilot", "run", "--repo", str(REPO), "--git-base", "HEAD",
           "--backend", "scripted", "--script", str(SCRIPTS), "--rounds", "0",
           "--timeout", "10", "--python", PYTHON, "--out", str(OUT)]
cli = subprocess.run(command, cwd=RUN, env=env, capture_output=True, text=True, timeout=45)
(RUN / "cli.stdout.log").write_text(cli.stdout, encoding="utf-8")
(RUN / "cli.stderr.log").write_text(cli.stderr, encoding="utf-8")
report = json.loads((OUT / "report.json").read_text()) if (OUT / "report.json").exists() else {}
alias = "tests/test_existing_testpilot.py"
originals_before = ((REPO / "sample.py").read_bytes() == SOURCE_AFTER.encode("utf-8")
                    and (REPO / "tests/test_existing.py").read_bytes() == EXISTING.encode("utf-8")
                    and not (REPO / alias).exists())
patch = OUT / "testpilot.patch"
check = subprocess.run(git_base + ["apply", "--check", str(patch)],
                       capture_output=True, text=True) if patch.exists() else None
apply = None
receiving = None
exact_applied = False
if check is not None and check.returncode == 0:
    apply = subprocess.run(git_base + ["apply", str(patch)], capture_output=True, text=True)
    if apply.returncode == 0:
        exact_applied = (REPO / alias).read_bytes() == GENERATED.encode("utf-8")
        receiving = subprocess.run([PYTHON, "-m", "pytest", "-q"], cwd=REPO, env=env,
                                   capture_output=True, text=True, timeout=30)
        (RUN / "receiving-pytest.stdout.log").write_text(receiving.stdout, encoding="utf-8")
        (RUN / "receiving-pytest.stderr.log").write_text(receiving.stderr, encoding="utf-8")
originals_after = ((REPO / "sample.py").read_bytes() == SOURCE_AFTER.encode("utf-8")
                   and (REPO / "tests/test_existing.py").read_bytes() == EXISTING.encode("utf-8"))
expected_source = SOURCE_AFTER[SOURCE_AFTER.index("def target():"):].removesuffix("\n")
selected = report.get("changed_functions", [])
checks = {
    "cli_exit_0": cli.returncode == 0,
    "report_passed": report.get("status") == "passed",
    "two_generated_tests": report.get("tests_written") == 2,
    "three_pipeline_pytest_passed": report.get("final", {}).get("passed") == 3,
    "exact_selected_source": len(selected) == 1 and selected[0]["source"] == expected_source,
    "exact_line_identity": len(selected) == 1 and
        (selected[0]["qualname"], selected[0]["lineno"], selected[0]["end_lineno"],
         selected[0]["changed_lines"]) == ("target", 4, 5, [5]),
    "alias_preserves_existing": sorted(report.get("test_files", {})) == [alias],
    "originals_before_apply": originals_before,
    "git_apply_check_0": check is not None and check.returncode == 0,
    "git_apply_0": apply is not None and apply.returncode == 0,
    "exact_applied_generated_bytes": exact_applied,
    "receiving_pytest_0": receiving is not None and receiving.returncode == 0,
    "receiving_three_passed": receiving is not None and "3 passed" in receiving.stdout,
    "originals_after_apply": originals_after,
}
manifest = json.loads((ROOT / "source-manifest.json").read_text())
checks["all_frozen_source_bytes_unchanged"] = all(
    hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() == pin["sha256"]
    for name, pin in manifest.items())
result = {"parent": "f1a8c8e6e7533eac5a23864ef56f4e769d0d9125",
          "python": sys.version, "command": command, "cli_returncode": cli.returncode,
          "checks": checks, "successful": all(checks.values()),
          "report_status": report.get("status"), "tests_written": report.get("tests_written"),
          "pipeline_final": report.get("final"), "coverage": report.get("coverage"),
          "selected": selected, "generated_alias": alias, "expected_generated": GENERATED,
          "git_apply_check": check.returncode if check else None,
          "git_apply_stderr": check.stderr if check else None,
          "git_apply": apply.returncode if apply else None,
          "receiving_pytest": {"returncode": receiving.returncode,
                               "stdout": receiving.stdout, "stderr": receiving.stderr}
                              if receiving else None,
          "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "source_manifest": manifest}
(ROOT / "combined-results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"successful": result["successful"], "checks": checks,
                  "harness_sha256": result["harness_sha256"],
                  "coverage_recorded": result["coverage"] is not None}, indent=2))
raise SystemExit(0 if result["successful"] else 1)
