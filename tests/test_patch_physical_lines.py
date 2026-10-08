"""Receive physical patch lines with native Git, including Unicode string content."""
import subprocess

import pytest

from testpilot.loop import make_patch


def git(repo, *args, patch=None):
    return subprocess.run(
        ["git", *args], cwd=repo, input=patch, text=True, encoding="utf-8",
        capture_output=True, timeout=10,
    )


@pytest.fixture
def repo(tmp_path):
    initialized = git(tmp_path, "init", "-q")
    assert initialized.returncode == 0, initialized.stderr
    return tmp_path


def receive(repo, content, *, additions_only):
    patch = make_patch(repo, {"tests/test_generated.py": content}, additions_only=additions_only)
    checked = git(repo, "apply", "--check", "-", patch=patch)
    assert checked.returncode == 0, checked.stderr
    applied = git(repo, "apply", "-", patch=patch)
    assert applied.returncode == 0, applied.stderr
    assert (repo / "tests/test_generated.py").read_bytes() == content.encode("utf-8")


@pytest.mark.parametrize("separator", ["\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"])
def test_added_patch_retains_non_lf_string_content(repo, separator):
    content = f'def test_generated():\n    assert "left{separator}right" == "left{separator}right"\n'
    compile(content, "tests/test_generated.py", "exec")
    receive(repo, content, additions_only=True)


@pytest.mark.parametrize("old_separator,new_separator", [
    ("\u2028", "-"), ("-", "\u2029"), ("\u2028", "\u2029"),
])
def test_modified_patch_counts_both_versions_as_physical_lines(repo, old_separator, new_separator):
    target = repo / "tests/test_generated.py"
    target.parent.mkdir()
    target.write_text(f'VALUE = "old{old_separator}text"\n', encoding="utf-8", newline="")
    content = f'VALUE = "new{new_separator}text"\n'
    compile(content, str(target), "exec")
    receive(repo, content, additions_only=False)


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_ordinary_physical_newlines_and_blank_lines_are_retained(repo, newline):
    content = newline.join(["def test_generated():", "    assert True", "", ""])
    receive(repo, content, additions_only=True)


def test_empty_or_unchanged_input_emits_no_patch(repo):
    target = repo / "tests/test_generated.py"
    target.parent.mkdir()
    content = 'VALUE = "one\u2028two"\n'
    target.write_text(content, encoding="utf-8", newline="")
    assert make_patch(repo, {}) == ""
    assert make_patch(repo, {"tests/test_generated.py": content}) == ""


def test_additions_only_patch_still_refuses_existing_test(repo):
    target = repo / "tests/test_generated.py"
    target.parent.mkdir()
    original = b"def test_original():\r\n    assert True\r\n"
    target.write_bytes(original)
    generated = "def test_generated():\n    assert True\n"
    patch = make_patch(repo, {"tests/test_generated.py": generated}, additions_only=True)
    assert "new file mode 100644\n" in patch
    checked = git(repo, "apply", "--check", "-", patch=patch)
    assert checked.returncode != 0
    assert "already exists" in checked.stderr
    assert target.read_bytes() == original
