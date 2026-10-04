import sys

import pytest

from testpilot.sandbox import clean_env, coverage_available, run_pytest


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "m.py").write_text("def f(x):\n    if x:\n        return 1\n    return 0\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_base.py").write_text("from m import f\n\n\ndef test_f():\n    assert f(1) == 1\n")
    return tmp_path


def test_pass_and_isolation(repo):
    extra = {"tests/test_new.py": "from m import f\n\n\ndef test_zero():\n    assert f(0) == 0\n"}
    r = run_pytest(repo, extra, timeout=30, coverage=False)
    assert r.ok and r.passed == 2 and r.failed == 0 and not r.timed_out
    assert not (repo / "tests" / "test_new.py").exists()  # original repo untouched


def test_failure_reported(repo):
    extra = {"tests/test_bad.py": "from m import f\n\n\ndef test_wrong():\n    assert f(0) == 5\n"}
    r = run_pytest(repo, extra, timeout=30, coverage=False)
    assert not r.ok and r.failed == 1 and r.passed == 1
    rep = r.failure_report()
    assert "test_wrong" in rep and "assert 0 == 5" in rep


def test_collection_error_counts_as_error(repo):
    r = run_pytest(repo, {"tests/test_imp.py": "import does_not_exist\n"}, timeout=30, coverage=False)
    assert not r.ok and r.errors >= 1


def test_timeout_kills(repo):
    r = run_pytest(repo, {"tests/test_hang.py": "def test_hang():\n    while True:\n        pass\n"},
                   timeout=2, coverage=False)
    assert r.timed_out and not r.ok and r.returncode is None
    assert r.duration_s < 10 and "TIMEOUT" in r.failure_report()


def test_rejects_escape(repo):
    with pytest.raises(ValueError):
        run_pytest(repo, {"../evil.py": "x"}, timeout=5, coverage=False)


def test_no_tests_is_not_ok(tmp_path):
    (tmp_path / "m.py").write_text("x = 1\n")
    assert not run_pytest(tmp_path, timeout=30, coverage=False).ok


def test_env_scrubbed(monkeypatch, tmp_path):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    monkeypatch.setenv("PYTEST_ADDOPTS", "-x")
    env = clean_env(tmp_path)
    assert "NEBIUS_API_KEY" not in env and "PYTEST_ADDOPTS" not in env
    assert str(tmp_path) in env["PYTHONPATH"]


@pytest.mark.skipif(not coverage_available(sys.executable), reason="coverage not installed")
def test_coverage_collected(repo):
    r = run_pytest(repo, timeout=60, coverage=True)
    assert r.coverage is not None
    assert r.coverage.executed("m.py") == {1, 2, 3}
    assert 4 in r.coverage.executable("m.py")
    assert "tests/test_base.py" not in r.coverage.files
