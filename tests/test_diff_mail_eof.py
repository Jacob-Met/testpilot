"""Git mail metadata must not consume a real no-newline deletion record."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from testpilot.diff import DiffFormatError, changed_functions, parse_unified_diff


ROOT = Path(__file__).resolve().parents[1]
EOF_MARKER = "\\ No newline at end of file"
EXPECTED = [{
    "path": "sample.py",
    "module": "sample",
    "qualname": "selected",
    "lineno": 1,
    "end_lineno": 2,
    "changed_lines": [2],
    "source": "def selected():\n    return 2",
    "is_method": False,
}]


def _fixture_env():
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_AUTHOR_DATE="2026-10-13T00:00:00+00:00",
        GIT_COMMITTER_DATE="2026-10-13T00:00:00+00:00",
    )
    return env


def _git(repo, *args, input=None, check=True):
    return subprocess.run(
        ["git", "-C", str(repo),
         "-c", "core.autocrlf=false", "-c", "core.hooksPath=" + os.devnull,
         "-c", "commit.gpgsign=false",
         "-c", "user.name=TestPilot mail fixture",
         "-c", "user.email=testpilot@example.invalid", *args],
        input=input, check=check, capture_output=True, timeout=15, env=_fixture_env(),
    )


def _change(tmp_path, *, note_name="z-notes.md", source_eof=True):
    repo = tmp_path / "project"
    repo.mkdir()
    _git(repo, "init", "-q")
    source = repo / "sample.py"
    note = repo / note_name
    source.write_bytes(b"def selected():\n    return 1\n")
    note.write_bytes(b"- " if source_eof else b"- \n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "Before change")
    source.write_bytes(b"def selected():\n    return 2\n")
    note.unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "Change selected and remove note")
    plain = _git(repo, "diff", "--no-ext-diff", "--no-textconv", "HEAD^", "HEAD").stdout
    assert _git(repo, "apply", "--reverse", "--check", "-", input=plain).returncode == 0
    assert [function.to_dict() for function in changed_functions(repo, plain.decode("utf-8"))] == EXPECTED
    return repo, plain


def _mail(repo, *options):
    patch = _git(repo, "format-patch", "--stdout", "--no-stat", *options, "-1").stdout
    assert patch.startswith(b"From ")
    assert _git(repo, "apply", "--reverse", "--check", "-", input=patch).returncode == 0
    return patch


def _snapshot(path):
    stat = path.stat()
    return path.read_bytes(), stat.st_ino, stat.st_size, stat.st_mtime_ns


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
@pytest.mark.parametrize("final_lf", [True, False], ids=["terminated", "unterminated"])
def test_unsigned_mail_terminal_eof_deletion_selects_complete_change(tmp_path, newline, final_lf):
    repo, _ = _change(tmp_path)
    patch = _mail(repo, "--no-signature")
    assert patch.endswith(b"-- \n\\ No newline at end of file\n")
    text = patch.decode("utf-8")
    if not final_lf:
        text = text.removesuffix("\n")
    text = text.replace("\n", newline)
    before = _snapshot(repo / "sample.py")
    files = parse_unified_diff(text)
    assert [change.path for change in files] == ["sample.py", "z-notes.md"]
    assert files[1].is_deleted and files[1].added_lines == set()
    assert [function.to_dict() for function in changed_functions(repo, text)] == EXPECTED
    assert _snapshot(repo / "sample.py") == before


@pytest.mark.parametrize("source_eof", [True, False], ids=["source-marker", "source-lf"])
@pytest.mark.parametrize("signature", [None, EOF_MARKER], ids=["git-version", "marker-signature"])
def test_complete_mail_keeps_version_and_marker_text_signatures(tmp_path, source_eof, signature):
    repo, _ = _change(tmp_path, source_eof=source_eof)
    options = () if signature is None else ("--signature=" + signature,)
    patch = _mail(repo, *options)
    if signature is not None:
        assert patch.endswith(("-- \n" + EOF_MARKER + "\n\n").encode("utf-8"))
    assert [function.to_dict() for function in changed_functions(repo, patch.decode("utf-8"))] == EXPECTED


def test_unsigned_eof_deletion_before_a_later_file_is_still_body(tmp_path):
    repo, _ = _change(tmp_path, note_name="a-notes.md")
    patch = _mail(repo, "--no-signature")
    assert b"-- \n\\ No newline at end of file\ndiff --git a/sample.py " in patch
    files = parse_unified_diff(patch.decode("utf-8"))
    assert [change.path for change in files] == ["a-notes.md", "sample.py"]
    assert files[0].is_deleted
    assert [function.to_dict() for function in changed_functions(repo, patch.decode("utf-8"))] == EXPECTED


def _targets(repo, diff_path, *, stdin=None):
    env = _fixture_env()
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(ROOT))
    # Keep the new actual CLI probes optimized when the test interpreter is.
    optimize = ["-O"] if sys.flags.optimize else []
    return subprocess.run(
        [sys.executable, *optimize, "-B", "-m", "testpilot", "targets",
         "--repo", str(repo), "--diff", str(diff_path), "--json"],
        cwd=repo.parent, env=env, input=stdin, capture_output=True, timeout=30,
    )


@pytest.mark.parametrize("route", ["file", "stdin"])
def test_targets_cli_receives_unsigned_terminal_deletion_from_file_and_stdin(tmp_path, route):
    repo, plain = _change(tmp_path)
    patch = _mail(repo, "--no-signature")
    saved = tmp_path / "unsigned.patch"
    # The saved-file route also exercises CRLF transport normalization.
    saved.write_bytes(patch.replace(b"\n", b"\r\n") if route == "file" else patch)
    before_patch = _snapshot(saved)
    before_source = _snapshot(repo / "sample.py")
    plain_result = _targets(repo, "-", stdin=plain)
    assert plain_result.returncode == 0, plain_result.stderr
    assert plain_result.stderr == b""
    expected = {"changed_functions": EXPECTED}
    assert json.loads(plain_result.stdout) == expected
    result = _targets(repo, saved if route == "file" else "-",
                      stdin=None if route == "file" else saved.read_bytes())
    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    assert json.loads(result.stdout) == expected
    assert result.stdout == plain_result.stdout
    assert _snapshot(saved) == before_patch
    assert _snapshot(repo / "sample.py") == before_source


@pytest.mark.parametrize("missing", ["old", "new"])
def test_eof_annotation_does_not_satisfy_a_missing_body_record(tmp_path, monkeypatch, missing):
    repo, _ = _change(tmp_path)
    patch = _mail(repo, "--no-signature")
    before = _snapshot(repo / "sample.py")
    old_header = b"@@ -1 +0,0 @@"
    assert patch.count(old_header) == 1
    replacement = b"@@ -1,2 +0,0 @@" if missing == "old" else b"@@ -1 +1,1 @@"
    damaged = patch.replace(old_header, replacement)
    assert _git(repo, "apply", "--reverse", "--check", "-", input=damaged,
                check=False).returncode != 0
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("source-read")
        raise AssertionError("incomplete mail reached source selection")

    monkeypatch.setattr("testpilot.diff.tokenize.open", forbidden)
    with pytest.raises(DiffFormatError, match="diff"):
        changed_functions(repo, damaged.decode("utf-8"))
    assert calls == []
    assert _snapshot(repo / "sample.py") == before
