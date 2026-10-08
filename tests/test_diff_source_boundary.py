"""A selected diff must not supply source from outside its repository."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from testpilot.diff import changed_functions
from testpilot.loop import TestPilot


SOURCE = 'def selected():\n    return "SYNTHETIC_SOURCE"\n'


def diff_for(path: str, *, quoted: bool = False) -> str:
    old, new = "a/" + path, "b/" + path
    if quoted:
        old, new = json.dumps(old, ensure_ascii=False), json.dumps(new, ensure_ascii=False)
    return (f"--- {old}\n+++ {new}\n@@ -1,2 +1,2 @@\n"
            ' def selected():\n-    return "before"\n+    return "SYNTHETIC_SOURCE"\n')


def paths(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text(SOURCE, encoding="utf-8")
    return repo, outside


@pytest.mark.parametrize("quoted", [False, True])
@pytest.mark.parametrize("kind", ["parent", "absolute", "file_link", "directory_link"])
def test_rejects_outside_source_before_read(tmp_path, monkeypatch, kind, quoted):
    repo, outside = paths(tmp_path)
    if kind == "parent":
        name = "../outside.py"
    elif kind == "absolute":
        name = outside.as_posix()
    elif kind == "file_link":
        (repo / "selected.py").symlink_to(outside)
        name = "selected.py"
    else:
        (repo / "linked").symlink_to(tmp_path, target_is_directory=True)
        name = "linked/outside.py"
    original = Path.read_text
    reads = []

    def observe(path, *args, **kwargs):
        reads.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", observe)
    with pytest.raises(ValueError, match="diff source"):
        changed_functions(repo, diff_for(name, quoted=quoted))
    assert reads == []
    assert outside.read_bytes() == SOURCE.encode()


@pytest.mark.parametrize("name", ["../missing.py", "/missing.py", "pkg/../selected.py"])
def test_invalid_diff_paths_are_not_silently_ignored(tmp_path, name):
    repo, _ = paths(tmp_path)
    (repo / "selected.py").write_text(SOURCE, encoding="utf-8")
    with pytest.raises(ValueError, match="diff source"):
        changed_functions(repo, diff_for(name))


@pytest.mark.parametrize("name", ["selected.py", "pkg/café.py", "pkg/file with spaces.py"])
def test_valid_relative_sources_keep_exact_identity(tmp_path, name):
    repo, _ = paths(tmp_path)
    target = repo / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(SOURCE, encoding="utf-8")
    functions = changed_functions(repo, diff_for(name, quoted=True))
    assert [(f.path, f.qualname, f.changed_lines, f.source) for f in functions] == [
        (name, "selected", [2], SOURCE.rstrip("\n"))]


def test_in_repo_symlink_and_symlinked_repo_root_are_supported(tmp_path):
    repo, _ = paths(tmp_path)
    (repo / "selected.py").write_text(SOURCE, encoding="utf-8")
    (repo / "alias.py").symlink_to("selected.py")
    root_alias = tmp_path / "repo-alias"
    root_alias.symlink_to(repo, target_is_directory=True)
    functions = changed_functions(root_alias, diff_for("alias.py"))
    assert [(f.path, f.qualname) for f in functions] == [("alias.py", "selected")]


def test_ignored_paths_and_missing_in_repo_sources_keep_existing_behavior(tmp_path):
    repo, outside = paths(tmp_path)
    (repo / "tests").mkdir()
    (repo / "tests/test_selected.py").symlink_to(outside)
    ignored = diff_for("../notes.md") + diff_for("tests/test_selected.py") + diff_for("missing.py")
    ignored += '--- a/../outside.py\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-def selected():\n-    pass\n'
    assert changed_functions(repo, ignored) == []
    with pytest.raises(ValueError, match="diff source"):
        changed_functions(repo, diff_for("tests/test_selected.py"), include_tests=True)


def test_pipeline_rejects_mixed_diff_before_baseline_or_model(tmp_path, monkeypatch):
    repo, _ = paths(tmp_path)
    (repo / "selected.py").write_text(SOURCE, encoding="utf-8")
    calls = []

    class Client:
        def chat(self, *args, **kwargs):
            calls.append("model")
            raise AssertionError("model must not receive outside source")

    def baseline(*args, **kwargs):
        calls.append("pytest")
        raise AssertionError("baseline must not run for invalid source paths")

    monkeypatch.setattr("testpilot.loop.run_pytest", baseline)
    with pytest.raises(ValueError, match="diff source"):
        TestPilot(Client()).run(repo, diff_for("selected.py") + diff_for("../outside.py"))
    assert calls == []


def test_cli_rejects_invalid_diff_as_configuration_error(tmp_path):
    repo, _ = paths(tmp_path)
    patch = tmp_path / "input.diff"
    patch.write_text(diff_for("../outside.py"), encoding="utf-8")
    script = tmp_path / "script"
    script.mkdir()
    (script / "01_plan.md").write_text("Must remain unused.\n", encoding="utf-8")
    output = tmp_path / "result"
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    run = subprocess.run(
        [sys.executable, "-m", "testpilot", "run", "--repo", str(repo),
         "--diff", str(patch), "--script", str(script), "--out", str(output)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10,
    )
    assert run.returncode == 2
    assert "testpilot: invalid diff source:" in run.stderr
    assert "Traceback" not in run.stderr
    assert run.stdout == ""
    assert not output.exists()
