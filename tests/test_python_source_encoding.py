"""Real Python source encodings must survive Git-to-AST source selection."""
from __future__ import annotations

import codecs
import os
from pathlib import Path
import subprocess
import sys

import pytest

from testpilot.diff import DiffSourceError, changed_functions


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", *args],
        cwd=repo, check=True, capture_output=True, timeout=10,
    ).stdout


def function(label: str, offset: int) -> str:
    # Keep non-ASCII source outside the changed hunk's three context lines.
    # This exercises source decoding through an ordinary UTF-8 Git diff.
    return (
        f'def price():\n    """Return the {label} price."""\n'
        "    total = 0\n"
        "    total += 1\n"
        "    total += 2\n"
        "    total += 3\n"
        "    total += 4\n"
        "    total += 5\n"
        f"    return total + {offset}\n"
    )


def edited_source(repo: Path, prefix: bytes, encoding: str, label: str, newline: bytes = b"\n"):
    git(repo, "init", "-q")
    source = repo / "price.py"

    def encoded(offset: int) -> bytes:
        return (prefix + function(label, offset).encode(encoding)).replace(b"\n", newline)

    source.write_bytes(encoded(1))
    git(repo, "add", "price.py")
    git(repo, "-c", "user.name=Encoding fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-qm", "original")
    source.write_bytes(encoded(2))
    diff = git(repo, "diff", "--no-ext-diff", "--no-textconv", "--unified=3").decode("utf-8")
    return source, diff


def python_import(repo: Path):
    return subprocess.run(
        [sys.executable, "-B", "-c", "import price; print(price.price())"],
        cwd=repo, capture_output=True, text=True, timeout=10,
    )


@pytest.mark.parametrize("prefix,encoding,label,newline", [
    (b"", "utf-8", "café", b"\n"),
    (b"# coding: utf-8\n", "utf-8", "café", b"\n"),
    (codecs.BOM_UTF8, "utf-8", "café", b"\n"),
    (codecs.BOM_UTF8 + b"# coding: utf-8\n", "utf-8", "café", b"\n"),
    (b"# coding: latin-1\n", "latin-1", "café", b"\n"),
    (b"#!/usr/bin/env python\n# coding: latin-1\n", "latin-1", "café", b"\n"),
    (b"# coding: cp1252\n", "cp1252", "café €", b"\n"),
    (b"#!/usr/bin/env python\n# coding: cp1252\n", "cp1252", "café €", b"\r\n"),
], ids=["default-utf8", "declared-utf8", "utf8-bom", "utf8-bom-cookie",
        "latin1-first-line", "latin1-second-line", "cp1252", "cp1252-crlf"])
def test_importable_source_keeps_decoded_function_and_line_identity(tmp_path, prefix, encoding, label, newline):
    source, diff = edited_source(tmp_path, prefix, encoding, label, newline)
    original = source.read_bytes()
    imported = python_import(tmp_path)
    assert imported.returncode == 0, imported.stderr
    assert imported.stdout == "17\n"

    selected = changed_functions(tmp_path, diff)

    assert len(selected) == 1
    target = selected[0]
    start = prefix.count(b"\n") + 1
    end = start + len(function(label, 2).splitlines()) - 1
    assert (target.path, target.module, target.qualname, target.is_method) == (
        "price.py", "price", "price", False)
    assert (target.lineno, target.end_lineno, target.changed_lines) == (start, end, [end])
    assert target.source == function(label, 2).rstrip("\n")
    assert source.read_bytes() == original


@pytest.mark.parametrize("prefix,encoding", [
    (b"# coding: not-a-python-codec\n", "utf-8"),
    (b"# coding: ascii\n", "utf-8"),
    (codecs.BOM_UTF8 + b"# coding: latin-1\n", "utf-8"),
    (b"", "latin-1"),
], ids=["unknown-codec", "declared-ascii-invalid-byte", "conflicting-bom-cookie", "invalid-default-utf8"])
def test_invalid_python_encoding_is_not_silently_replaced(tmp_path, prefix, encoding):
    source, diff = edited_source(tmp_path, prefix, encoding, "café")
    original = source.read_bytes()
    assert python_import(tmp_path).returncode != 0

    with pytest.raises((SyntaxError, UnicodeDecodeError)):
        changed_functions(tmp_path, diff)

    assert source.read_bytes() == original


@pytest.mark.parametrize("kind", ["parent", "absolute", pytest.param(
    "symlink", marks=pytest.mark.skipif(os.name == "nt", reason="Windows symlinks need optional privileges"),
)])
def test_containment_precedes_any_source_open(tmp_path, kind):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_bytes(codecs.BOM_UTF8 + b"def price():\n    return 2\n")
    inside = repo / "inside.py"
    inside.write_bytes(b"def price():\n    return 2\n")
    if kind == "parent":
        path = "../outside.py"
    elif kind == "absolute":
        path = outside.as_posix()
    else:
        (repo / "alias.py").symlink_to(outside)
        path = "alias.py"

    def diff_for(name):
        return f"--- a/{name}\n+++ b/{name}\n@@ -1,2 +1,2 @@\n def price():\n-    return 1\n+    return 2\n"

    # Audit the real open operation across both Path.read_text and tokenize.open.
    # Disable this hook afterwards; CPython audit hooks cannot be removed.
    opens = []
    active = True

    def observe(event, args):
        if active and event == "open" and isinstance(args[0], (str, bytes)):
            opens.append(os.fsdecode(args[0]))

    sys.addaudithook(observe)
    try:
        with pytest.raises(DiffSourceError):
            changed_functions(repo, diff_for(path))
        assert opens == []
        assert len(changed_functions(repo, diff_for("inside.py"))) == 1
        assert opens == [str(inside)]
    finally:
        active = False
