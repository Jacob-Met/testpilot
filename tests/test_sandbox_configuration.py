"""Receive pytest configuration discovery through native copied-project runs."""
import tempfile

import pytest

from testpilot.sandbox import run_pytest


@pytest.fixture
def surrounded_project(tmp_path, monkeypatch):
    """A caller's temporary directory belongs to an unrelated pytest project."""
    project = tmp_path / "target"
    (project / "selected").mkdir(parents=True)
    (project / "legacy").mkdir()
    (project / "selected/test_selected.py").write_text(
        "def test_selected():\n    assert True\n")
    (project / "legacy/test_actual_failure.py").write_text(
        "def test_actual_failure():\n"
        "    assert False, 'LEGACY-FAILURE-MUST-BE-RECEIVED'\n")
    unrelated = tmp_path / "unrelated-project"
    native_tmp = unrelated / "temporary"
    native_tmp.mkdir(parents=True)
    (unrelated / "pytest.ini").write_text("[pytest]\ntestpaths = selected\n")
    for name in ("TMPDIR", "TEMP", "TMP"):
        monkeypatch.setenv(name, str(native_tmp))
    monkeypatch.setattr(tempfile, "tempdir", str(native_tmp))
    return project


def assert_real_failure(result, *, passed):
    assert result.junit_available and not result.timed_out
    assert result.returncode == 1 and not result.ok, result.output
    assert result.passed == passed and result.failed == 1
    assert result.errors == result.skipped == 0
    assert any(case.outcome == "failed" and "LEGACY-FAILURE-MUST-BE-RECEIVED" in case.message
               for case in result.cases)


@pytest.mark.parametrize("inert_pyproject", [False, True])
def test_unconfigured_target_does_not_inherit_unrelated_testpaths(surrounded_project, inert_pyproject):
    project = surrounded_project
    if inert_pyproject:
        (project / "pyproject.toml").write_text(
            '[project]\nname = "unconfigured-target"\nversion = "0.0.0"\n')
    originals = {p.relative_to(project): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    assert_real_failure(run_pytest(project, coverage=False, timeout=5), passed=1)
    assert {p.relative_to(project): p.read_bytes() for p in project.rglob("*") if p.is_file()} == originals


@pytest.mark.parametrize("name, content", [
    ("pytest.ini", "[pytest]\ntestpaths = legacy\n"),
    (".pytest.ini", "[pytest]\ntestpaths = legacy\n"),
    ("pyproject.toml", '[tool.pytest.ini_options]\ntestpaths = ["legacy"]\n'),
    ("tox.ini", "[pytest]\ntestpaths = legacy\n"),
    ("setup.cfg", "[tool:pytest]\ntestpaths = legacy\n"),
])
def test_target_native_configuration_and_relative_paths_are_preserved(surrounded_project, name, content):
    project = surrounded_project
    config = project / name
    config.write_text(content)
    assert_real_failure(run_pytest(project, coverage=False, timeout=5), passed=0)
    assert config.read_text() == content


def test_target_empty_pytest_ini_still_stops_ancestor_discovery(surrounded_project):
    (surrounded_project / "pytest.ini").write_text("")
    assert_real_failure(run_pytest(surrounded_project, coverage=False, timeout=5), passed=1)


def test_explicit_native_test_selection_is_preserved(surrounded_project):
    result = run_pytest(surrounded_project, coverage=False, timeout=5,
                        pytest_args=("-k", "test_selected"))
    assert result.ok and result.junit_available
    assert result.passed == 1 and result.failed == result.errors == result.skipped == 0
    assert len(result.cases) == 1 and result.cases[0].nodeid.endswith("::test_selected")


def test_explicit_native_configuration_override_is_preserved(surrounded_project):
    result = run_pytest(surrounded_project, coverage=False, timeout=5,
                        pytest_args=("-o", "testpaths=legacy"))
    assert_real_failure(result, passed=0)


def library_project(tmp_path):
    project = tmp_path / "library-project"
    (project / "lib").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "lib/config_path_dependency.py").write_text("VALUE = 731\n")
    (project / "tests/test_library.py").write_text(
        "from config_path_dependency import VALUE\n"
        "def test_library():\n    assert VALUE == 731\n")
    return project


@pytest.mark.parametrize("unrelated_config", [False, True])
def test_explicit_relative_pythonpath_keeps_the_project_base(tmp_path, monkeypatch, unrelated_config):
    project = library_project(tmp_path)
    parent = tmp_path / "temporary-parent"
    native_tmp = parent / "tmp"
    native_tmp.mkdir(parents=True)
    if unrelated_config:
        (parent / "pytest.ini").write_text("[pytest]\ntestpaths = nonexistent\n")
    monkeypatch.setattr(tempfile, "tempdir", str(native_tmp))
    originals = {p.relative_to(project): p.read_bytes() for p in project.rglob("*") if p.is_file()}
    result = run_pytest(project, coverage=False, timeout=5,
                        pytest_args=("-o", "pythonpath=lib"))
    assert result.ok and result.junit_available, result.output
    assert result.passed == 1 and result.failed == result.errors == result.skipped == 0
    assert {p.relative_to(project): p.read_bytes() for p in project.rglob("*") if p.is_file()} == originals


def test_explicit_config_bypasses_malformed_default_and_keeps_its_path_base(tmp_path):
    project = library_project(tmp_path)
    (project / "pytest.ini").write_text("[malformed\n")
    (project / "configuration").mkdir()
    (project / "configuration/alternate.ini").write_text("[pytest]\npythonpath = ../lib\n")
    result = run_pytest(project, coverage=False, timeout=5,
                        pytest_args=("-c", "configuration/alternate.ini"))
    assert result.ok and result.junit_available, result.output
    assert result.passed == 1 and result.failed == result.errors == 0


def test_selected_nested_configuration_keeps_its_relative_path_base(tmp_path):
    project = library_project(tmp_path)
    (project / "tests/pytest.ini").write_text("[pytest]\npythonpath = ../lib\n")
    result = run_pytest(project, coverage=False, timeout=5, pytest_args=("tests",))
    assert result.ok and result.junit_available, result.output
    assert result.passed == 1 and result.failed == result.errors == 0


def test_malformed_default_configuration_still_refuses(tmp_path):
    project = library_project(tmp_path)
    (project / "pytest.ini").write_text("[malformed\n")
    result = run_pytest(project, coverage=False, timeout=5)
    assert not result.ok and result.returncode == 4 and not result.junit_available
    assert "pytest.ini" in result.output and "ERROR" in result.output


@pytest.mark.skipif(pytest.version_tuple < (9, 0), reason="native TOML configuration requires pytest 9")
@pytest.mark.parametrize("name, content", [
    ("pytest.toml", '[pytest]\ntestpaths = ["legacy"]\n'),
    (".pytest.toml", '[pytest]\ntestpaths = ["legacy"]\n'),
    ("pyproject.toml", '[tool.pytest]\ntestpaths = ["legacy"]\n'),
])
def test_native_toml_target_configuration_is_preserved(surrounded_project, name, content):
    (surrounded_project / name).write_text(content)
    assert_real_failure(run_pytest(surrounded_project, coverage=False, timeout=5), passed=0)
