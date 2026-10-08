"""Native Git and Python controls for physical source-line identity."""
import subprocess

import pytest

from testpilot.diff import changed_functions, functions_touching, parse_unified_diff


SEPARATORS = [
    pytest.param("\f", id="formfeed"),
    pytest.param("\x85", id="next-line"),
    pytest.param("\u2028", id="line-separator"),
    pytest.param("\u2029", id="paragraph-separator"),
]


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True, text=True,
    ).stdout


def _context_change(repo, separator, newline="\n"):
    _git(repo, "init", "-q")
    _git(repo, "config", "core.autocrlf", "false")
    path = repo / "sample.py"
    before = f'note = "left{separator}right"\n\ndef answer():\n    return 1\n'
    after = before.replace("return 1", "return 2")
    path.write_bytes(before.replace("\n", newline).encode("utf-8"))
    _git(repo, "add", "sample.py")
    _git(
        repo, "-c", "user.name=Synthetic native fixture",
        "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Baseline",
    )
    path.write_bytes(after.replace("\n", newline).encode("utf-8"))
    namespace = {}
    exec(compile(path.read_bytes(), str(path), "exec"), namespace)
    assert namespace["answer"]() == 2
    return _git(repo, "diff", "--", "sample.py")


@pytest.mark.parametrize("separator", SEPARATORS)
def test_real_git_context_retains_the_changed_function(tmp_path, separator):
    diff = _context_change(tmp_path, separator)
    changes = parse_unified_diff(diff)
    assert len(changes) == 1
    assert changes[0].added_lines == {4}
    selected = changed_functions(tmp_path, diff)
    assert [(item.qualname, item.lineno, item.end_lineno, item.changed_lines)
            for item in selected] == [("answer", 3, 4, [4])]
    assert selected[0].source == "def answer():\n    return 2"


@pytest.mark.parametrize("separator", SEPARATORS)
def test_selected_source_preserves_valid_literal_characters(separator):
    source = f'def answer():\n    return "left{separator}right"\n'
    original = {}
    exec(compile(source, "literal.py", "exec"), original)
    selected = functions_touching(source, "literal.py", {2}, {2})
    assert len(selected) == 1
    assert selected[0].source == source[:-1]
    reconstructed = {}
    exec(compile(selected[0].source, "selected.py", "exec"), reconstructed)
    assert reconstructed["answer"]() == original["answer"]()


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"], ids=["lf", "crlf", "cr"])
def test_python_physical_newlines_keep_source_spans(newline):
    source = newline.join(["def answer():", "    return 'value'", ""])
    selected = functions_touching(source, "physical.py", {2}, {2})
    assert len(selected) == 1
    assert (selected[0].lineno, selected[0].end_lineno) == (1, 2)
    assert selected[0].source == "def answer():\n    return 'value'"


def test_real_git_crlf_source_keeps_unicode_context(tmp_path):
    diff = _context_change(tmp_path, "\u2028", "\r\n")
    selected = changed_functions(tmp_path, diff)
    assert [item.qualname for item in selected] == ["answer"]
    assert selected[0].changed_lines == [4]
    assert selected[0].source == "def answer():\n    return 2"
