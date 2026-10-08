"""Exercise the public diff/target boundary using real Git pathname output."""
import os
import subprocess

import pytest

from testpilot.diff import changed_functions, parse_unified_diff


OLD = "def price():\n    return 1\n"
NEW = "def price():\n    return 2\n"


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "core.autocrlf=false", "-c", "core.hooksPath=/dev/null",
         *args], check=True, capture_output=True, text=True, encoding="utf-8",
    ).stdout


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "-c", "user.name=Authored Test", "-c", "user.email=authored@example.invalid",
        "commit", "--allow-empty", "-qm", "authored baseline")
    return tmp_path


def write(repo, path, content):
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def track(repo, path, content=OLD):
    write(repo, path, content)
    git(repo, "--literal-pathspecs", "add", "--", path)
    git(repo, "-c", "user.name=Authored Test", "-c", "user.email=authored@example.invalid",
        "commit", "-qm", "authored source")


@pytest.mark.parametrize("quoted", ["true", "false"])
@pytest.mark.parametrize("path", ["café.py", "日本語.py", "src/πακέτο/δelta.py"])
def test_unicode_git_paths_reach_changed_function_selection(repo, path, quoted):
    track(repo, path)
    write(repo, path, NEW)
    diff = git(repo, "-c", f"core.quotePath={quoted}", "diff", "--")
    changes = parse_unified_diff(diff)
    assert [(item.path, item.old_path) for item in changes] == [(path, path)]
    assert changes[0].added_lines == {2}
    functions = changed_functions(repo, diff)
    assert [(item.path, item.qualname, item.changed_lines) for item in functions] == [(path, "price", [2])]
    assert functions[0].source == NEW.rstrip("\n")


@pytest.mark.parametrize("quoted", ["true", "false"])
@pytest.mark.parametrize("path", [
    'quote"name.py', "back\\slash.py", "tab\tname.py", "line\nname.py",
    "return\rname.py", "café\tname.py",
])
@pytest.mark.skipif(os.name != "posix", reason="control characters, quotes and literal backslashes require POSIX filenames")
def test_git_escaped_filenames_preserve_exact_path(repo, path, quoted):
    track(repo, path)
    write(repo, path, NEW)
    diff = git(repo, "-c", f"core.quotePath={quoted}", "diff", "--")
    changes = parse_unified_diff(diff)
    assert [(item.path, item.old_path) for item in changes] == [(path, path)]
    assert [(item.path, item.qualname) for item in changed_functions(repo, diff)] == [(path, "price")]


def test_quoted_new_and_deleted_paths_keep_dev_null_meaning(repo):
    deleted, added = "café.py", "新しい.py"
    track(repo, deleted)
    (repo / deleted).unlink()
    write(repo, added, NEW)
    git(repo, "--literal-pathspecs", "add", "-A", "--")
    diff = git(repo, "-c", "core.quotePath=true", "diff", "--cached", "--no-renames", "--")
    changes = {item.path: item for item in parse_unified_diff(diff)}
    assert set(changes) == {deleted, added}
    assert changes[deleted].is_deleted and changes[deleted].old_path == deleted
    assert changes[added].is_new and changes[added].old_path is None
    assert [(item.path, item.qualname) for item in changed_functions(repo, diff)] == [(added, "price")]


def test_quoted_rename_with_change_uses_new_worktree_path(repo):
    old, new = "café.py", "déplacé.py"
    content = OLD + "\n" + "\n".join(f"VALUE_{i} = {i}" for i in range(20)) + "\n"
    track(repo, old, content)
    git(repo, "mv", "--", old, new)
    write(repo, new, content.replace("return 1", "return 2"))
    diff = git(repo, "-c", "core.quotePath=true", "diff", "HEAD", "--find-renames=20%", "--")
    assert "rename from" in diff
    changes = parse_unified_diff(diff)
    assert [(item.path, item.old_path) for item in changes] == [(new, old)]
    assert [(item.path, item.qualname, item.changed_lines) for item in changed_functions(repo, diff)] == [(new, "price", [2])]


def test_quoted_test_paths_remain_excluded_by_default(repo):
    path = "tests/test_café.py"
    track(repo, path)
    write(repo, path, NEW)
    diff = git(repo, "-c", "core.quotePath=true", "diff", "--")
    assert changed_functions(repo, diff) == []
    assert [(item.path, item.qualname) for item in changed_functions(repo, diff, include_tests=True)] == [(path, "price")]


def test_unquoted_spaces_and_diff_u_timestamps_are_unchanged(repo):
    path = "folder with spaces/mod.py"
    track(repo, path)
    write(repo, path, NEW)
    diff = git(repo, "diff", "--")
    assert parse_unified_diff(diff)[0].path == path
    stamp = "\t2026-10-08 00:00:00.000000000 +0000"
    unified = f"--- a/{path}{stamp}\n+++ b/{path}{stamp}\n@@ -1,2 +1,2 @@\n def price():\n-    return 1\n+    return 2\n"
    assert [(item.path, item.qualname) for item in changed_functions(repo, unified)] == [(path, "price")]


@pytest.mark.parametrize("header", [
    '"b/unclosed.py', '"b/trailing\\"', '"b/bad\\x41.py"', '"b/bad\\u00e9.py"',
    '"b/bad\\1.py"', '"b/bad\\777.py"', '"b/nul\\000.py"', '"b/name.py"junk',
])
def test_malformed_git_quoted_header_is_explicitly_refused(header):
    diff = f"--- /dev/null\n+++ {header}\n@@ -0,0 +1,2 @@\n+def price():\n+    return 2\n"
    with pytest.raises(ValueError, match="Git-quoted"):
        parse_unified_diff(diff)


@pytest.mark.skipif(os.name != "posix", reason="arbitrary non-UTF-8 filenames require a POSIX filesystem")
def test_octal_filename_bytes_round_trip_through_the_filesystem(repo):
    path = os.fsdecode(b"raw_\xff.py")
    track(repo, path)
    write(repo, path, NEW)
    diff = git(repo, "-c", "core.quotePath=true", "diff", "--")
    assert os.fsencode(parse_unified_diff(diff)[0].path) == b"raw_\xff.py"
    assert [(item.path, item.qualname) for item in changed_functions(repo, diff)] == [(path, "price")]
