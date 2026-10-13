"""The public version query must finish before command work begins."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

import testpilot
from testpilot import __main__ as cli


def test_version_exits_before_command_work(capsys):
    tripwire = AssertionError("version query entered command work")
    with (
        patch.object(cli, "_read_diff", side_effect=tripwire),
        patch.object(cli, "make_client", side_effect=tripwire),
        patch.object(cli.RoutingConfig, "from_env", side_effect=tripwire),
        patch.object(cli, "TestPilot", side_effect=tripwire),
        patch.object(cli, "write_outputs", side_effect=tripwire),
        pytest.raises(SystemExit) as result,
    ):
        cli.main(["--version"])
    assert result.value.code == 0
    captured = capsys.readouterr()
    assert captured.out == f"testpilot {testpilot.__version__}\n"
    assert captured.err == ""


def test_module_version_from_an_unrelated_directory_preserves_files(tmp_path):
    sentinel = tmp_path / "conftest.py"
    sentinel.write_bytes(b"raise AssertionError('project tests must not be loaded')\n")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    env = {
        "PATH": os.defpath,
        "PYTHONPATH": str(Path(testpilot.__file__).resolve().parent.parent),
        "PYTHONDONTWRITEBYTECODE": "1",
        "TESTPILOT_BACKEND": "version-must-not-construct-a-client",
        "TESTPILOT_PRICES": "deliberately invalid JSON",
    }
    result = subprocess.run(
        [sys.executable, "-B", "-m", "testpilot", "--version"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"testpilot {testpilot.__version__}\n"
    assert result.stderr == ""
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_help_and_required_command_remain_available(capsys):
    with pytest.raises(SystemExit) as help_result:
        cli.main(["--help"])
    assert help_result.value.code == 0
    help_text = capsys.readouterr()
    assert "--version" in help_text.out
    for command in ("run", "targets", "recheck", "regression", "compare"):
        assert command in help_text.out
    assert help_text.err == ""

    with pytest.raises(SystemExit) as missing:
        cli.main([])
    assert missing.value.code == 2
    error = capsys.readouterr()
    assert error.out == ""
    assert "the following arguments are required: cmd" in error.err
