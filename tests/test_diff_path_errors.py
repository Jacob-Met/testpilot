"""Malformed path headers use the parser's native whole-diff error boundary."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from testpilot.diff import DiffFormatError, parse_unified_diff


ROOT = Path(__file__).resolve().parents[1]
VALID = "--- a/valid.py\n+++ b/valid.py\n@@ -1,2 +1,2 @@\n def answer():\n-    return 1\n+    return 2\n"
MALFORMED = [
    '"b/unclosed.py', '"b/trailing\\"', '"b/bad\\x41.py"', '"b/bad\\u00e9.py"',
    '"b/bad\\1.py"', '"b/bad\\777.py"', '"b/nul\\000.py"', '"b/name.py"junk',
]


def damaged_patch(header: str, side: str, prefix: str = "") -> str:
    old = header if side == "old" else "a/valid.py"
    new = header if side == "new" else "b/valid.py"
    return prefix + f"--- {old}\n+++ {new}\n@@ -1,2 +1,2 @@\n def answer():\n-    return 1\n+    return 2\n"


@pytest.mark.parametrize("header", MALFORMED)
@pytest.mark.parametrize("side", ["old", "new"])
@pytest.mark.parametrize("prefix", ["", VALID], ids=["first-file", "later-file"])
def test_malformed_path_rejects_the_whole_diff_with_its_record(header, side, prefix):
    record = prefix.count("\n") + (1 if side == "old" else 2)
    with pytest.raises(DiffFormatError, match=rf"record {record}: .*Git-quoted") as caught:
        parse_unified_diff(damaged_patch(header, side, prefix))
    assert isinstance(caught.value.__cause__, ValueError)
    assert not isinstance(caught.value.__cause__, DiffFormatError)


def cli(*args: object, input_text: str | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-B", "-m", "testpilot", *map(str, args)],
        cwd=ROOT, env=env, input=input_text, capture_output=True,
        text=True, encoding="utf-8", timeout=30,
    )


@pytest.mark.parametrize("command", ["run", "targets"])
@pytest.mark.parametrize("side", ["old", "new"])
@pytest.mark.parametrize("route", ["file", "stdin"])
def test_native_cli_refuses_bad_path_before_model_setup_and_preserves_output(tmp_path, command, side, route):
    project = tmp_path / "project"
    project.mkdir()
    source = project / "valid.py"
    source.write_text("def answer():\n    return 2\n", encoding="utf-8")
    output = tmp_path / "retained"
    output.mkdir()
    retained = {name: ("keep original " + name + "\n").encode("utf-8")
                for name in ("report.json", "report.html", "report.md", "testpilot.patch")}
    for name, data in retained.items():
        (output / name).write_bytes(data)
    patch = damaged_patch('"b/bad\\x41.py"', side, VALID)
    diff = tmp_path / "change.diff"
    diff.write_text(patch, encoding="utf-8")
    args = [command, "--repo", project, "--diff", "-" if route == "stdin" else diff]
    if command == "run":
        args += ["--backend", "scripted", "--script", tmp_path / "missing-responses", "--out", output]
    else:
        args += ["--json"]
    result = cli(*args, input_text=patch if route == "stdin" else None)
    assert result.returncode == 2, result.stderr
    assert result.stdout == ""
    boundary = "invalid diff format" if command == "run" else "cannot inspect targets"
    assert result.stderr.startswith(f"testpilot: {boundary}:")
    assert f"record {7 if side == 'old' else 8}:" in result.stderr
    assert "Git-quoted" in result.stderr
    assert "Traceback" not in result.stderr
    assert "missing-responses" not in result.stderr
    assert {path.name: path.read_bytes() for path in output.iterdir()} == retained
    assert source.read_bytes() == b"def answer():\n    return 2\n"


@pytest.mark.parametrize("quoted", ["true", "false"])
def test_real_git_unicode_path_retains_the_actual_cli_target(tmp_path, quoted):
    project = tmp_path / "project"
    project.mkdir()
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)

    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(project), "-c", "core.hooksPath=" + os.devnull,
             "-c", "commit.gpgsign=false", *args],
            check=True, capture_output=True, env=env, timeout=30,
        )

    git("init", "-q")
    source = project / "café.py"
    source.write_text("def answer():\n    return 1\n", encoding="utf-8")
    git("add", ".")
    git("-c", "user.name=TestPilot Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-qm", "before")
    git("config", "core.quotePath", quoted)
    source.write_text("def answer():\n    return 2\n", encoding="utf-8")
    result = cli("targets", "--repo", project, "--git-base", "HEAD", "--json")
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert json.loads(result.stdout)["changed_functions"] == [{
        "path": "café.py", "module": "café", "qualname": "answer", "lineno": 1,
        "end_lineno": 2, "changed_lines": [2], "source": "def answer():\n    return 2",
        "is_method": False,
    }]
    assert source.read_bytes() == b"def answer():\n    return 2\n"
