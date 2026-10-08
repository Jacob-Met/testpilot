"""Exercise the public CLI with a dependency installed only in a project venv."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import venv

import pytest


ROOT = Path(__file__).resolve().parents[1]
DEPENDENCY = "testpilot_project_only_dependency"
SOURCE = f"from {DEPENDENCY} import offset\n\ndef adjusted(value):\n    return value + offset\n"
DIFF = "--- /dev/null\n+++ b/subject.py\n@@ -0,0 +1,4 @@\n" + "".join(
    "+" + line + "\n" for line in SOURCE.splitlines()
)


@pytest.fixture
def project(tmp_path):
    repo = tmp_path / "project source"
    (repo / "tests").mkdir(parents=True)
    (repo / "subject.py").write_text(SOURCE)
    (repo / "tests/test_existing.py").write_text(
        f"from {DEPENDENCY} import record\nfrom subject import adjusted\n\n"
        "def test_existing():\n    record('existing')\n    assert adjusted(1) == 42\n"
    )
    diff = tmp_path / "change.diff"
    diff.write_text(DIFF)
    script = tmp_path / "script"
    script.mkdir()
    (script / "01_plan.md").write_text("Check the adjusted value, including zero.")
    for filename, expected in [("02_tests.md", 42), ("03_repair.md", 41)]:
        (script / filename).write_text(
            "```python path=tests/test_adjusted.py\n"
            f"from {DEPENDENCY} import record\nfrom subject import adjusted\n\n"
            "def test_zero():\n    record('generated')\n"
            f"    assert adjusted(0) == {expected}\n```\n"
        )
    return repo, diff, script


@pytest.fixture
def prepared_python(tmp_path):
    environment = tmp_path / "physical" / "prepared environment"
    venv.EnvBuilder(with_pip=False, symlinks=os.name != "nt").create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    purelib = Path(subprocess.check_output(
        [str(python), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"], text=True,
    ).strip())
    # Reuse installed test tooling without downloads. The authored dependency
    # below lives only in this prepared venv, outside the project being copied.
    tooling = Path(pytest.__file__).resolve().parent.parent
    (purelib / "test-tooling.pth").write_text(str(tooling) + "\n")
    (purelib / f"{DEPENDENCY}.py").write_text(
        "import json, os, sys\noffset = 41\n"
        "def record(label):\n"
        "    with open(os.environ['PROJECT_ENV_RECEIPT'], 'a') as receipt:\n"
        "        receipt.write(json.dumps({'label': label, 'prefix': sys.prefix, "
        "'executable': sys.executable}) + '\\n')\n"
    )
    assert importlib.util.find_spec(DEPENDENCY) is None
    return python, environment


def invoke(tmp_path, project, arguments=(), env_extra=None):
    repo, diff, script = project
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1")
    for name in list(env):
        if name.startswith("TESTPILOT_"):
            env.pop(name)
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, "-m", "testpilot", "run", "--repo", str(repo), "--diff", str(diff),
         "--script", str(script), "--backend", "scripted", "--rounds", "1", "--timeout", "15",
         "--out", str(tmp_path / "output"), *arguments],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=45,
    )


@pytest.mark.parametrize("spelling", ["absolute", "relative", "path", pytest.param(
    "symlink-parent", marks=pytest.mark.skipif(os.name == "nt", reason="directory symlinks need optional Windows privileges"),
)])
def test_project_environment_runs_baseline_generation_and_repair(tmp_path, project, prepared_python, spelling):
    python, environment = prepared_python
    receipt = tmp_path / "executions.jsonl"
    env = {"PROJECT_ENV_RECEIPT": str(receipt)}
    selected = str(python)
    if spelling == "relative":
        selected = os.path.relpath(python, tmp_path)
    elif spelling == "path":
        selected = python.name
        env["PATH"] = str(python.parent) + os.pathsep + os.environ.get("PATH", "")
    elif spelling == "symlink-parent":
        child = environment.parent / "child"
        child.mkdir()
        (tmp_path / "bridge").symlink_to(child, target_is_directory=True)
        selected = str(Path("bridge") / ".." / environment.name / python.parent.name / python.name)
    repo, _, _ = project
    original = {p.relative_to(repo).as_posix(): p.read_bytes() for p in repo.rglob("*") if p.is_file()}

    result = invoke(tmp_path, project, ["--python", selected], env)

    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((tmp_path / "output/report.json").read_text())
    assert report["status"] == "passed"
    assert report["repair_rounds_used"] == 1
    assert report["tests_written"] == 1
    assert report["rounds"][0]["result"]["failed"] == 1
    assert report["final"]["passed"] == 2
    if importlib.util.find_spec("coverage"):
        assert report["coverage"]["changed_lines_after"] == 100.0
    executions = [json.loads(line) for line in receipt.read_text().splitlines()]
    assert len(executions) == 5  # baseline, then existing+generated in each round
    assert all(item["prefix"] == str(environment) for item in executions)
    assert all(item["executable"] == str(python) for item in executions)
    assert [item["label"] for item in executions].count("generated") == 2
    assert original == {p.relative_to(repo).as_posix(): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    patch = tmp_path / "output/testpilot.patch"
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=repo, check=True, capture_output=True)
    assert "+++ b/tests/test_adjusted.py" in patch.read_text()
    assert (tmp_path / "output/report.md").is_file()


def test_default_interpreter_remains_the_tool_environment(tmp_path, project, prepared_python):
    # The prepared environment exists, but omission must not auto-select it.
    result = invoke(tmp_path, project)
    assert result.returncode == 1, result.stderr + result.stdout
    report = json.loads((tmp_path / "output/report.json").read_text())
    assert report["status"] == "failed"
    assert DEPENDENCY in report["final"]["output"]
    assert "ModuleNotFoundError" in report["final"]["output"]


@pytest.mark.parametrize("kind", ["missing", "directory", "not-executable"])
def test_invalid_interpreter_is_a_configuration_error_before_outputs(tmp_path, project, kind):
    selected = tmp_path / "invalid python"
    if kind == "directory":
        selected.mkdir()
    elif kind == "not-executable":
        selected.write_text("not an executable\n")
        selected.chmod(0o644)
    result = invoke(tmp_path, project, ["--python", str(selected)])
    assert result.returncode == 2
    assert "--python" in result.stderr
    assert "not found or not executable" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "output").exists()


def test_missing_optional_flag_still_runs_a_dependency_free_project(tmp_path, project):
    repo, diff, script = project
    source = "def adjusted(value):\n    return value + 41\n"
    (repo / "subject.py").write_text(source)
    diff.write_text("--- /dev/null\n+++ b/subject.py\n@@ -0,0 +1,2 @@\n" + "".join(
        "+" + line + "\n" for line in source.splitlines()
    ))
    (repo / "tests/test_existing.py").write_text("from subject import adjusted\ndef test_existing():\n    assert adjusted(1) == 42\n")
    (script / "02_tests.md").write_text(
        "```python path=tests/test_adjusted.py\nfrom subject import adjusted\n"
        "def test_zero():\n    assert adjusted(0) == 41\n```\n"
    )
    result = invoke(tmp_path, project)
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((tmp_path / "output/report.json").read_text())
    assert report["status"] == "passed"
    assert report["repair_rounds_used"] == 0
    assert report["final"]["passed"] == 2
