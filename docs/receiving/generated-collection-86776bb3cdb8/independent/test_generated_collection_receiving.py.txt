"""Independent collection/acceptance checks using real native pytest subprocesses."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from testpilot import sandbox as sandbox_module
from testpilot.loop import count_tests
from testpilot.sandbox import run_pytest


def project(tmp_path, *, testpaths="checks", conftest=""):
    repo = tmp_path / "authored-project"
    repo.mkdir()
    (repo / testpaths).mkdir()
    (repo / "pyproject.toml").write_text(
        f'[tool.pytest.ini_options]\ntestpaths = ["{testpaths}"]\n',
        encoding="utf-8",
    )
    if conftest:
        (repo / "conftest.py").write_text(conftest, encoding="utf-8")
    return repo


def run(repo, files=None, **kwargs):
    return run_pytest(
        repo, files, coverage=False, timeout=10, python=sys.executable, **kwargs
    )


def test_configured_suite_and_only_requested_generated_file_are_kept(tmp_path):
    repo = project(tmp_path)
    (repo / "checks/test_existing.py").write_text(
        'def test_existing():\n    assert False, "configured suite must remain"\n'
    )
    (repo / "tests").mkdir()
    (repo / "tests/test_unselected.py").write_text(
        'def test_unselected():\n    assert False, "ambient test must remain excluded"\n'
    )
    result = run(repo, {"tests/test_generated.py": "def test_generated():\n    assert True\n"})
    assert not result.ok
    assert (result.passed, result.failed) == (1, 1), result.to_dict()
    assert "configured suite must remain" in result.failure_report()
    assert "ambient test must remain excluded" not in result.output


def test_selected_directory_and_generated_file_overlap_executes_once(tmp_path):
    repo = project(tmp_path, testpaths="tests")
    (repo / "tests/test_existing.py").write_text("def test_existing():\n    assert True\n")
    generated = (
        "from pathlib import Path\n"
        "def test_generated():\n"
        "    counter = Path(__file__).with_name('executions.txt')\n"
        "    calls = int(counter.read_text()) + 1 if counter.exists() else 1\n"
        "    counter.write_text(str(calls))\n"
        "    assert calls == 1, 'generated test was executed twice'\n"
    )
    result = run(repo, {"tests/test_generated.py": generated})
    assert result.ok, result.to_dict()
    assert result.passed == 2


def test_helper_beside_generated_case_keeps_conftest_fixture_and_hook(tmp_path):
    repo = project(
        tmp_path,
        conftest=(
            "import pytest\n"
            "@pytest.fixture\n"
            "def authored_fixture():\n    return 29\n"
            "def pytest_collection_modifyitems(items):\n"
            "    for item in items:\n"
            "        item.user_properties.append(('authored_hook', 'kept'))\n"
        ),
    )
    (repo / "checks/test_existing.py").write_text("def test_existing():\n    assert True\n")
    generated = (
        "from pathlib import Path\n"
        "def test_generated(authored_fixture, request):\n"
        "    assert authored_fixture == 29\n"
        "    assert ('authored_hook', 'kept') in request.node.user_properties\n"
        "    assert Path(__file__).with_name('test_helper.py').is_file()\n"
    )
    result = run(
        repo,
        {
            "tests/test_helper.py": "HELPER_VALUE = 29\n",
            "tests/test_generated.py": generated,
        },
    )
    assert result.ok, result.to_dict()
    assert result.passed == 2
    assert count_tests({"tests/test_helper.py": "", "tests/test_generated.py": ""}, result, set()) == 1


@pytest.mark.parametrize(
    "generated",
    [
        "HELPER_VALUE = 29\n",
        "import pytest\npytest.skip('authored module skip', allow_module_level=True)\n",
        "import pytest\n@pytest.mark.skip(reason='authored case skip')\ndef test_generated():\n    assert False\n",
    ],
    ids=["helper-only", "module-skip", "all-cases-skipped"],
)
def test_unexecuted_generated_output_cannot_certify_success(tmp_path, generated):
    repo = project(tmp_path, testpaths="tests")
    (repo / "tests/test_existing.py").write_text("def test_existing():\n    assert True\n")
    result = run(repo, {"tests/test_generated.py": generated})
    assert result.passed == 1
    assert not result.ok, result.to_dict()
    assert "generated" in result.failure_report().lower()


def test_collection_hook_deselection_remains_effective(tmp_path):
    repo = project(
        tmp_path,
        testpaths="tests",
        conftest=(
            "def pytest_collection_modifyitems(config, items):\n"
            "    removed = [item for item in items if item.path.name == 'test_generated.py']\n"
            "    items[:] = [item for item in items if item not in removed]\n"
            "    config.hook.pytest_deselected(items=removed)\n"
        ),
    )
    (repo / "tests/test_existing.py").write_text("def test_existing():\n    assert True\n")
    result = run(repo, {"tests/test_generated.py": "def test_generated():\n    assert False\n"})
    assert result.failed == 0 and result.passed == 1
    assert not result.ok, result.to_dict()


def test_explicit_keyword_selector_cannot_masquerade_as_generated_success(tmp_path):
    repo = project(tmp_path, testpaths="tests")
    (repo / "tests/test_existing.py").write_text("def test_native():\n    assert True\n")
    result = run(
        repo,
        {"tests/test_generated.py": "def test_generated():\n    assert False\n"},
        pytest_args=("-k", "native"),
    )
    assert result.failed == 0 and result.passed == 1
    assert not result.ok, result.to_dict()


def test_generated_count_uses_provenance_when_existing_parameters_change(tmp_path):
    repo = project(
        tmp_path,
        testpaths="tests",
        conftest=(
            "from pathlib import Path\n"
            "def pytest_generate_tests(metafunc):\n"
            "    if 'authored_value' in metafunc.fixturenames:\n"
            "        added = Path(__file__).with_name('tests').joinpath('test_generated.py').is_file()\n"
            "        metafunc.parametrize('authored_value', [0, 1] if added else [0])\n"
        ),
    )
    (repo / "tests/test_existing.py").write_text(
        "def test_existing(authored_value):\n    assert authored_value >= 0\n"
    )
    args = ("--junitprefix", "authored.prefix")
    before = run(repo, pytest_args=args)
    generated = {"tests/test_generated.py": "def test_generated():\n    assert True\n"}
    after = run(repo, generated, pytest_args=args)
    assert before.ok and before.passed == 1
    assert after.ok and after.passed == 3, after.to_dict()
    assert count_tests(generated, after, {case.nodeid for case in before.cases}) == 1


def test_baseline_without_generated_files_keeps_native_success(tmp_path):
    repo = project(tmp_path)
    (repo / "checks/test_existing.py").write_text("def test_existing():\n    assert True\n")
    result = run(repo)
    assert result.ok and result.passed == 1


def test_real_scripted_cli_repairs_a_failure_outside_testpaths(tmp_path):
    repo = project(tmp_path)
    (repo / "m.py").write_text("def double(value):\n    return value * 2\n")
    (repo / "checks/test_existing.py").write_text(
        "from m import double\ndef test_existing():\n    assert double(3) == 6\n"
    )
    diff = tmp_path / "change.diff"
    diff.write_text(
        "--- /dev/null\n+++ b/m.py\n@@ -0,0 +1,2 @@\n"
        "+def double(value):\n+    return value * 2\n"
    )
    scripts = tmp_path / "script"
    scripts.mkdir()
    (scripts / "01_plan.md").write_text("Check the ordinary double result.\n")
    fence = chr(96) * 3
    body = (
        f"{fence}python path=tests/test_generated.py\n"
        "from m import double\n"
        "def test_generated():\n"
        "    assert double(2) == EXPECTED\n"
        f"{fence}\n"
    )
    (scripts / "02_tests.md").write_text(body.replace("EXPECTED", "5"))
    (scripts / "03_repair.md").write_text(body.replace("EXPECTED", "4"))
    out = tmp_path / "reported"
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(Path(sandbox_module.__file__).resolve().parents[1])
    command = [
        sys.executable, "-B", "-m", "testpilot", "run",
        "--repo", str(repo), "--diff", str(diff),
        "--backend", "scripted", "--script", str(scripts),
        "--rounds", "1", "--timeout", "10",
        "--python", sys.executable, "--out", str(out),
    ]
    process = subprocess.run(command, cwd=tmp_path, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=35)
    assert process.returncode == 0, process.stdout
    report = json.loads((out / "report.json").read_text())
    assert report["status"] == "passed"
    assert report["repair_rounds_used"] == 1, report
    assert report["rounds"][0]["result"]["failed"] == 1
    assert report["final"]["passed"] == 2
    assert report["tests_written"] == 1
    assert "assert double(2) == 4" in report["patch"]
    assert "assert double(2) == 5" not in report["patch"]
    assert not (repo / "tests/test_generated.py").exists()

