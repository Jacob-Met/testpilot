"""Exercise the public coverage choice with real pytest runs and authored inputs."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import venv

import pytest


ROOT = Path(__file__).resolve().parents[1]
HAS_COVERAGE = importlib.util.find_spec("coverage") is not None
DEPENDENCY = "testpilot_coverage_project_dependency"
FENCE = chr(96) * 3


def snapshot(root):
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*") if p.is_file()
    }


def project(tmp_path, *, broken_coverage=False, failing=False, repair=False, dependency=False):
    repo = tmp_path / "project with spaces"
    (repo / "tests").mkdir(parents=True)
    source = ("from " + DEPENDENCY + " import fee\n\n") if dependency else "fee = 7\n\n"
    source += "def add_fee(value):\n    return value + fee\n"
    (repo / "subject.py").write_text(source, encoding="utf-8")
    record = (
        "import json, os, sys\n"
        "def record(label):\n"
        "    with open(os.environ['COVERAGE_RECEIVING_EXECUTIONS'], 'a', encoding='utf-8') as stream:\n"
        "        stream.write(json.dumps({'label': label, 'prefix': sys.prefix, "
        "'executable': sys.executable}) + '\\n')\n"
    )
    (repo / "fixture_receipt.py").write_text(record, encoding="utf-8")
    (repo / "tests/test_existing.py").write_text(
        "from subject import add_fee\nfrom fixture_receipt import record\n\n"
        "def test_existing_fee():\n    record('existing')\n    assert add_fee(3) == 10\n",
        encoding="utf-8",
    )
    (repo / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n', encoding="utf-8",
    )
    if broken_coverage:
        (repo / ".coveragerc").write_text(
            "[run]\nplugins = authored_coverage_failure\n", encoding="utf-8",
        )
        (repo / "authored_coverage_failure.py").write_text(
            "def coverage_init(reg, options):\n"
            "    raise RuntimeError('authored optional coverage plugin cannot initialize')\n",
            encoding="utf-8",
        )
    diff = tmp_path / "change.diff"
    diff.write_text(
        "--- /dev/null\n+++ b/subject.py\n@@ -0,0 +1," + str(len(source.splitlines())) + " @@\n"
        + "".join("+" + line + "\n" for line in source.splitlines()), encoding="utf-8",
    )
    script = tmp_path / "scripted replies"
    script.mkdir()
    (script / "00-plan.md").write_text("Check add_fee with a distinct input.\n", encoding="utf-8")
    for index, expected in enumerate(([19, 18] if repair else [19 if failing else 18]), start=1):
        (script / f"{index:02d}-tests.md").write_text(
            FENCE + "python path=tests/test_generated_fee.py\n"
            "from subject import add_fee\nfrom fixture_receipt import record\n\n"
            "def test_generated_fee():\n    record('generated')\n"
            f"    assert add_fee(11) == {expected}\n" + FENCE + "\n", encoding="utf-8",
        )
    return repo, diff, script


def invoke(tmp_path, fixture, *arguments, label="run", rounds=0):
    repo, diff, script = fixture
    before = snapshot(repo)
    out = tmp_path / f"{label}-out"
    executions = tmp_path / f"{label}-executions.jsonl"
    temporary = tmp_path / f"{label}-temporary"
    temporary.mkdir()
    env = {
        key: value for key, value in os.environ.items()
        if not key.startswith("TESTPILOT_") and not key.startswith("COVERAGE")
    }
    env.update(
        PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        COVERAGE_RECEIVING_EXECUTIONS=str(executions), TMPDIR=str(temporary),
    )
    command = [
        sys.executable, "-B", "-m", "testpilot", "run",
        "--repo", str(repo), "--diff", str(diff),
        "--backend", "scripted", "--script", str(script),
        "--rounds", str(rounds), "--timeout", "15", "--out", str(out), *arguments,
    ]
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60)
    (tmp_path / f"{label}-stdout.log").write_text(result.stdout, encoding="utf-8")
    (tmp_path / f"{label}-stderr.log").write_text(result.stderr, encoding="utf-8")
    report_path = out / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None
    records = [json.loads(line) for line in executions.read_text().splitlines()] if executions.exists() else []
    unchanged = before == snapshot(repo)
    (tmp_path / f"{label}-receipt.json").write_text(
        json.dumps({
            "command": command, "returncode": result.returncode, "report": report,
            "executions": records, "project_unchanged": unchanged,
        }, indent=2) + "\n", encoding="utf-8",
    )
    assert unchanged, "the checked project must remain untouched"
    return result, report, records


def assert_success(result, report):
    assert result.returncode == 0, result.stderr + result.stdout
    assert report["status"] == "passed"
    assert report["final"]["returncode"] == 0
    assert report["final"]["passed"] == 2
    assert report["final"]["failed"] == 0
    assert report["tests_written"] == 1


@pytest.mark.parametrize("disabled", [False, True])
def test_default_and_explicit_choice_keep_successful_tests(tmp_path, disabled):
    result, report, records = invoke(
        tmp_path, project(tmp_path), *(["--no-coverage"] if disabled else []),
    )
    assert_success(result, report)
    assert len(records) == 3  # baseline existing; final existing and generated.
    if disabled or not HAS_COVERAGE:
        assert report["coverage"] is None
    else:
        assert report["coverage"] is not None
        assert report["coverage"]["changed_lines_after"] == 100.0
    assert "+++ b/tests/test_generated_fee.py" in report["patch"]


@pytest.mark.skipif(not HAS_COVERAGE, reason="coverage needed for the optional-plugin boundary")
def test_disable_bypasses_only_the_broken_optional_instrumentation(tmp_path):
    fixture = project(tmp_path, broken_coverage=True)
    default, measured, default_records = invoke(tmp_path, fixture, label="default")
    assert default.returncode == 1
    assert measured["status"] == "failed"
    assert "authored optional coverage plugin cannot initialize" in measured["final"]["output"]
    assert default_records == []

    result, report, records = invoke(tmp_path, fixture, "--no-coverage", label="disabled")
    assert_success(result, report)
    assert report["coverage"] is None
    assert len(records) == 3


def test_disable_preserves_a_real_generated_test_failure(tmp_path):
    result, report, records = invoke(
        tmp_path, project(tmp_path, broken_coverage=True, failing=True), "--no-coverage",
    )
    assert result.returncode == 1, result.stderr + result.stdout
    assert report["status"] == "failed"
    assert report["final"]["returncode"] == 1
    assert report["final"]["passed"] == 1
    assert report["final"]["failed"] == 1
    assert "assert 18 == 19" in report["final"]["output"]
    assert report["coverage"] is None
    assert report["repair_rounds_used"] == 0
    assert len(records) == 3


def test_disable_reaches_baseline_generation_and_repair(tmp_path):
    result, report, records = invoke(
        tmp_path, project(tmp_path, broken_coverage=True, repair=True),
        "--no-coverage", rounds=1,
    )
    assert_success(result, report)
    assert report["repair_rounds_used"] == 1
    assert [r["kind"] for r in report["rounds"]] == ["generate", "repair"]
    assert report["rounds"][0]["result"]["failed"] == 1
    assert report["rounds"][1]["result"]["passed"] == 2
    assert report["coverage"] is None
    assert len(records) == 5
    assert [r["label"] for r in records].count("generated") == 2
    assert "== 19" in report["rounds"][0]["contents"]["tests/test_generated_fee.py"]
    assert "== 18" in report["patch"]


def test_disable_composes_with_the_selected_project_python(tmp_path):
    fixture = project(tmp_path, broken_coverage=True, dependency=True)
    environment = tmp_path / "prepared environment"
    venv.EnvBuilder(with_pip=False, symlinks=os.name != "nt").create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    purelib = Path(subprocess.check_output(
        [str(python), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"], text=True,
    ).strip())
    (purelib / "test-tooling.pth").write_text(str(Path(pytest.__file__).resolve().parent.parent) + "\n")
    (purelib / f"{DEPENDENCY}.py").write_text("fee = 7\n", encoding="utf-8")
    assert importlib.util.find_spec(DEPENDENCY) is None

    default, default_report, _ = invoke(tmp_path, fixture, "--no-coverage", label="unprepared")
    assert default.returncode == 1
    assert "ModuleNotFoundError" in default_report["final"]["output"]
    assert DEPENDENCY in default_report["final"]["output"]

    result, report, records = invoke(
        tmp_path, fixture, "--no-coverage", "--python", str(python), label="prepared",
    )
    assert_success(result, report)
    assert report["coverage"] is None
    assert len(records) == 3
    assert all(r["prefix"] == str(environment) for r in records)
    assert all(r["executable"] == str(python) for r in records)
