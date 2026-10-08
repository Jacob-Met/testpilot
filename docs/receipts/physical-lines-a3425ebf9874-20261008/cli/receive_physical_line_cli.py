"""Run the real TestPilot CLI against an authored Git change, without a provider.

The baseline must miss the valid changed function. The candidate must select it,
produce two scripted tests, and deliver a patch that passes after application.
All writes stay under --work; neither source tree is edited.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-source", type=Path, required=True)
    parser.add_argument("--candidate-source", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    project = work / "project"
    project.mkdir()
    (project / "tests").mkdir()
    responses = work / "responses"
    responses.mkdir()
    before = 'note = "left\u2028right"\n\ndef answer():\n    return 1\n'
    after = before.replace("return 1", "return 2")
    original_test = 'from sample import note\n\ndef test_existing_note():\n    assert note.startswith("left")\n'
    (project / "sample.py").write_text(before, encoding="utf-8")
    (project / "tests/test_existing.py").write_text(original_test, encoding="utf-8")
    (project / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n', encoding="utf-8",
    )
    (responses / "01-plan.txt").write_text(
        "Check the changed return value and preserve the literal Unicode note.\n",
        encoding="utf-8",
    )
    (responses / "02-tests.txt").write_text(
        "```python path=tests/test_physical_line_consumer.py\n"
        "from sample import answer, note\n\n"
        "def test_changed_answer():\n    assert answer() == 2\n\n"
        'def test_literal_note():\n    assert note == "left\\u2028right"\n'
        "```\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["TESTPILOT_BACKEND"] = "scripted"
    env["TESTPILOT_PLANNER_MODEL"] = "fixture-planner"
    env["TESTPILOT_EDITOR_MODEL"] = "fixture-editor"
    env["TESTPILOT_PRICES"] = "{}"
    commands = []

    def run(argv, *, cwd=project, label, source=None):
        current_env = env.copy()
        if source is not None:
            current_env["PYTHONPATH"] = str(source.resolve())
        proc = subprocess.run(
            [str(part) for part in argv], cwd=cwd, env=current_env,
            capture_output=True, text=True, timeout=90,
        )
        (work / f"{label}.stdout.txt").write_text(proc.stdout, encoding="utf-8")
        (work / f"{label}.stderr.txt").write_text(proc.stderr, encoding="utf-8")
        commands.append({
            "label": label, "argv": [str(part) for part in argv], "cwd": str(cwd),
            "returncode": proc.returncode,
            "source_path": str(source.resolve()) if source else None,
        })
        return proc

    def git(*parts, label):
        proc = run(["git", *parts], label=label)
        assert proc.returncode == 0, (label, proc.stderr)
        return proc.stdout.strip()

    git("init", "-q", label="git-init")
    git("config", "core.autocrlf", "false", label="git-newlines")
    git("add", "sample.py", "tests", "pyproject.toml", label="git-add")
    git("-c", "user.name=Synthetic native fixture", "-c",
        "user.email=fixture@example.invalid", "commit", "-qm", "Baseline",
        label="git-commit")
    fixture_base = git("rev-parse", "HEAD", label="git-head")
    (project / "sample.py").write_text(after, encoding="utf-8")
    namespace = {}
    exec(compile(after, "sample.py", "exec"), namespace)
    assert namespace["answer"]() == 2
    watched = ["sample.py", "tests/test_existing.py", "pyproject.toml"]
    input_hashes = {path: sha(project / path) for path in watched}
    patch = git("diff", "HEAD", "--", "*.py", label="git-diff")
    (work / "input.diff").write_text(patch + "\n", encoding="utf-8")

    results = {}
    for label, source in [
        ("baseline", args.baseline_source), ("candidate", args.candidate_source),
    ]:
        out = work / f"{label}-output"
        proc = run(
            [sys.executable, "-B", "-m", "testpilot", "run", "--repo", project,
             "--git-base", "HEAD", "--backend", "scripted", "--script", responses,
             "--rounds", "0", "--timeout", "20", "--out", out],
            label=f"{label}-cli", source=source,
        )
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        assert {path: sha(project / path) for path in watched} == input_hashes
        assert not (project / "tests/test_physical_line_consumer.py").exists()
        results[label] = {
            "returncode": proc.returncode, "report": report,
            "output_sha256": {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()},
            "source_commit": subprocess.check_output(
                ["git", "-C", str(source), "rev-parse", "HEAD"], text=True,
            ).strip(),
            "source_module_sha256": sha(source / "testpilot/diff.py"),
        }

    baseline, candidate = results["baseline"], results["candidate"]
    assert baseline["returncode"] == 1
    assert baseline["report"]["status"] == "no_changes"
    assert baseline["report"]["changed_functions"] == []
    assert baseline["report"]["ledger"]["entries"] == []
    assert baseline["report"]["tests_written"] == 0
    assert baseline["report"]["patch"] == ""
    assert candidate["returncode"] == 0
    assert candidate["report"]["status"] == "passed"
    assert len(candidate["report"]["changed_functions"]) == 1
    selected = candidate["report"]["changed_functions"][0]
    assert (selected["qualname"], selected["lineno"], selected["end_lineno"],
            selected["changed_lines"]) == ("answer", 3, 4, [4])
    assert candidate["report"]["tests_written"] == 2
    assert [entry["role"] for entry in candidate["report"]["ledger"]["entries"]] == [
        "planner", "editor",
    ]

    receiving = work / "patch-receiver"
    shutil.copytree(project, receiving)
    patch_path = work / "candidate-output/testpilot.patch"
    check = run(
        ["git", "apply", "--check", patch_path], cwd=receiving, label="patch-check",
    )
    assert check.returncode == 0, check.stderr
    apply = run(["git", "apply", patch_path], cwd=receiving, label="patch-apply")
    assert apply.returncode == 0, apply.stderr
    assert {path: sha(receiving / path) for path in watched} == input_hashes
    test = run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "--junitxml=" + str(work / "delivered-tests.xml")],
        cwd=receiving, label="delivered-tests",
    )
    assert test.returncode == 0, test.stdout + test.stderr
    import xml.etree.ElementTree as ET
    junit = ET.parse(work / "delivered-tests.xml").getroot()
    cases = list(junit.iter("testcase"))
    assert len(cases) == 3
    assert not list(junit.iter("failure"))
    assert not list(junit.iter("error"))
    assert not list(junit.iter("skipped"))
    assert {path: sha(receiving / path) for path in watched} == input_hashes
    receipt = {
        "schema": "hamon.testpilot.physical_line_cli_receiving.v1",
        "qualification": "PASS",
        "claim": "https://github.com/Jacob-Met/testpilot/issues/16",
        "python": sys.version,
        "fixture_base": fixture_base,
        "fixture_input_sha256": input_hashes,
        "original_source_and_existing_test_preserved": True,
        "baseline_expected_feature_failure": {
            key: baseline[key] for key in ("returncode", "source_commit", "source_module_sha256")
        },
        "baseline_status": baseline["report"]["status"],
        "candidate": {
            key: candidate[key] for key in ("returncode", "source_commit", "source_module_sha256")
        },
        "candidate_status": candidate["report"]["status"],
        "selected_function": selected,
        "scripted_calls": len(candidate["report"]["ledger"]["entries"]),
        "generated_tests": candidate["report"]["tests_written"],
        "delivered_patch_check": check.returncode,
        "delivered_patch_apply": apply.returncode,
        "delivered_existing_plus_generated_tests": len(cases),
        "provider_calls": 0,
        "commands": commands,
        "report_and_patch_sha256": {
            label: result["output_sha256"] for label, result in results.items()
        },
    }
    (work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "qualification": receipt["qualification"],
        "baseline_status": receipt["baseline_status"],
        "baseline_exit": baseline["returncode"],
        "candidate_status": receipt["candidate_status"],
        "candidate_exit": candidate["returncode"],
        "scripted_calls": receipt["scripted_calls"],
        "generated_tests": receipt["generated_tests"],
        "delivered_tests_passed": len(cases),
        "receipt_path": str(work / "receipt.json"),
        "receipt_sha256": sha(work / "receipt.json"),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
