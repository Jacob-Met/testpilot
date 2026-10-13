"""Default automatic selection excludes test files behind in-repo aliases."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from testpilot import diff as diff_module
from testpilot.diff import DiffSourceError, changed_functions

SOURCE = 'def selected():\n    return "synthetic source"\n'


def patch_for(name: str) -> str:
    return (f"--- a/{name}\n+++ b/{name}\n@@ -1,2 +1,2 @@\n"
            ' def selected():\n-    return "old"\n+    return "synthetic source"\n')


def write_source(repo: Path, name: str, source: str = SOURCE) -> Path:
    target = repo / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    return target


def link(alias: Path, target: str | Path, *, directory: bool = False) -> None:
    try:
        alias.symlink_to(target, target_is_directory=directory)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")


@pytest.mark.parametrize("destination", [
    "tests/helper.py", "test/helper.py", "pkg/test_subject.py",
    "pkg/subject_test.py", "pkg/conftest.py",
])
def test_resolved_test_labels_are_excluded_before_source_read(tmp_path, monkeypatch, destination):
    repo = tmp_path / "repo"
    repo.mkdir()
    target = write_source(repo, destination)
    link(repo / "alias.py", destination)
    opened = []
    original_open = diff_module.tokenize.open

    def observe(path):
        opened.append(path)
        return original_open(path)

    monkeypatch.setattr(diff_module.tokenize, "open", observe)
    assert changed_functions(repo, patch_for("alias.py")) == []
    assert opened == []

    included = changed_functions(repo, patch_for("alias.py"), include_tests=True)
    assert [(f.path, f.qualname, f.source) for f in included] == [
        ("alias.py", "selected", SOURCE.rstrip("\n"))]
    assert opened == [target]


def test_directory_alias_and_symlinked_repo_root_keep_test_exclusion(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    write_source(repo, "tests/helper.py")
    link(repo / "linked", "tests", directory=True)
    link(tmp_path / "repo-alias", repo, directory=True)
    assert changed_functions(tmp_path / "repo-alias", patch_for("linked/helper.py")) == []
    included = changed_functions(tmp_path / "repo-alias", patch_for("linked/helper.py"),
                                 include_tests=True)
    assert [(f.path, f.qualname) for f in included] == [("linked/helper.py", "selected")]


def test_unreadable_test_source_is_not_decoded_through_an_alias(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    target = write_source(repo, "tests/helper.py")
    target.write_bytes(b"\xff\n")
    link(repo / "alias.py", "tests/helper.py")
    opened = []
    original_open = diff_module.tokenize.open

    def observe(path):
        opened.append(path)
        return original_open(path)

    monkeypatch.setattr(diff_module.tokenize, "open", observe)
    assert changed_functions(repo, patch_for("alias.py")) == []
    assert opened == []


@pytest.mark.parametrize("destination", ["pkg/subject.py", "pkg/source.txt"])
def test_non_test_aliases_keep_original_labels_and_supported_suffixes(tmp_path, destination):
    # Only the destination relative to the repository is classified. An
    # ancestor directory named tests must not turn all source into test source.
    repo = tmp_path / "tests" / "project"
    repo.mkdir(parents=True)
    write_source(repo, destination)
    link(repo / "alias.py", destination)
    for include_tests in (False, True):
        functions = changed_functions(repo, patch_for("alias.py"), include_tests=include_tests)
        assert [(f.path, f.module, f.qualname, f.changed_lines, f.source) for f in functions] == [
            ("alias.py", "alias", "selected", [2], SOURCE.rstrip("\n"))]


def test_confinement_precedes_resolved_test_exclusion(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = write_source(tmp_path, "outside/tests/helper.py")
    link(repo / "alias.py", outside)
    opened = []
    monkeypatch.setattr(diff_module.tokenize, "open", lambda path: opened.append(path))
    with pytest.raises(DiffSourceError, match="outside"):
        changed_functions(repo, patch_for("alias.py"))
    assert opened == []


def test_lexical_test_exclusion_keeps_its_existing_precedence(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = write_source(tmp_path, "outside/subject.py")
    link(repo / "test_alias.py", outside)
    assert changed_functions(repo, patch_for("test_alias.py")) == []
    with pytest.raises(DiffSourceError, match="outside"):
        changed_functions(repo, patch_for("test_alias.py"), include_tests=True)


def test_mixed_changes_keep_only_source_alias_in_visit_order(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    write_source(repo, "tests/helper.py")
    write_source(repo, "pkg/subject.py")
    link(repo / "hidden.py", "tests/helper.py")
    link(repo / "source.py", "pkg/subject.py")
    changes = patch_for("hidden.py") + patch_for("source.py") + patch_for("hidden.py")
    assert [(f.path, f.qualname) for f in changed_functions(repo, changes)] == [
        ("source.py", "selected")]


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is required for the native diff")
def test_actual_git_symlink_diff_stays_out_of_cli_target_preview(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    write_source(repo, "tests/helper.py")
    link(repo / "alias.py", "tests/helper.py")
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "add", "alias.py"], check=True, capture_output=True)
    raw = subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "--no-ext-diff", "--no-textconv",
         "--no-color", "--src-prefix=a/", "--dst-prefix=b/", "--", "alias.py"],
        check=True, capture_output=True,
    ).stdout
    assert b"new file mode 120000" in raw
    patch = tmp_path / "symlink.diff"
    patch.write_bytes(raw)
    before = (repo / "tests/helper.py").read_bytes()
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    result = subprocess.run(
        [sys.executable, "-m", "testpilot", "targets", "--repo", str(repo),
         "--diff", str(patch), "--json"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {"changed_functions": []}
    assert (repo / "tests/helper.py").read_bytes() == before
    assert (repo / "alias.py").readlink() == Path("tests/helper.py")
