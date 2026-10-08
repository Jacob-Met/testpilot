"""Receive complete unified hunks before selecting or executing Python targets."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

from testpilot.diff import DiffFormatError, changed_functions, parse_unified_diff
from testpilot.loop import TestPilot
from testpilot.model import ScriptedModel


ROOT = Path(__file__).resolve().parents[1]
HEADER = "--- a/sample.py\n+++ b/sample.py\n"
VALID = HEADER + "@@ -1,2 +1,2 @@\n def selected():\n-    return 1\n+    return 2\n"
INVALID = [
    pytest.param(VALID.rsplit("+    return 2", 1)[0], id="truncated-addition"),
    pytest.param(VALID.replace("-1,2 +1,2", "-1,3 +1,3"), id="missing-context-at-eof"),
    pytest.param(VALID + "+extra\n", id="extra-addition"),
    pytest.param(VALID + "-extra\n", id="extra-deletion"),
    pytest.param(VALID + "-- \n2.53.0\n\n", id="mail-footer-outside-envelope"),
    pytest.param(VALID + " extra\n", id="extra-context"),
    pytest.param(HEADER + "@@ -0,0 +1,1 @@\n-deleted\n+added\n", id="old-range-underflow"),
    pytest.param(HEADER + "@@ -1,1 +0,0 @@\n+added\n-deleted\n", id="new-range-underflow"),
    pytest.param(HEADER + "@@ -0,0 +1,2 @@\n context\n+added\n", id="context-with-no-old-lines"),
    pytest.param(HEADER + "@@ -1,1 +1,1 @@\nunprefixed\n", id="invalid-body-prefix"),
    pytest.param(HEADER + "@@ -one +two @@\n-old\n+new\n", id="malformed-range"),
    pytest.param("@@ -1 +1 @@\n-old\n+new\n", id="missing-file-headers"),
    pytest.param("+++ b/sample.py\n@@ -1 +1 @@\n-old\n+new\n", id="missing-old-header"),
    pytest.param(HEADER, id="headers-without-hunk"),
    pytest.param(VALID.replace("-1,2 +1,2", "-1,4 +1,4") + VALID, id="next-file-before-end"),
    pytest.param(VALID.replace("-1,2 +1,2", "-1,4 +1,4") +
                 "@@ -5 +5 @@\n-old\n+new\n", id="next-hunk-before-end"),
    pytest.param(HEADER + "@@ -0,1 +1,1 @@\n-old\n+new\n", id="nonempty-range-at-zero"),
]


@pytest.mark.parametrize("diff_text", INVALID)
def test_inconsistent_hunks_are_not_partial_success(diff_text):
    with pytest.raises(ValueError, match="diff"):
        parse_unified_diff(diff_text)


def _fixture_env():
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return env


def _git(repo, *args, check=True, input=None):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=check, capture_output=True,
        text=True, input=input, timeout=15, env=_fixture_env(),
    )


@pytest.fixture
def git_change(tmp_path):
    repo = tmp_path / "project"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "core.autocrlf", "false")
    source = repo / "sample.py"
    source.write_text("def selected():\n    return 1\n", encoding="utf-8")
    _git(repo, "add", "sample.py")
    source.write_text("def selected():\n    return 2\n", encoding="utf-8")
    diff_text = _git(repo, "diff", "--no-ext-diff", "--no-textconv", "--", "sample.py").stdout
    return repo, diff_text


def _missing_context(diff_text):
    match = re.search(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@", diff_text)
    assert match is not None
    old_start, old_count, new_start, new_count = map(int, match.groups())
    changed = f"@@ -{old_start},{old_count + 1} +{new_start},{new_count + 1} @@"
    return diff_text[:match.start()] + changed + diff_text[match.end():]


def test_actual_git_patch_and_corrupted_counter_have_distinct_outcomes(git_change):
    repo, real_diff = git_change
    reverse = _git(repo, "apply", "--reverse", "--check", "-", input=real_diff)
    assert reverse.returncode == 0
    selected = changed_functions(repo, real_diff)
    assert [(f.qualname, f.changed_lines, f.source) for f in selected] == [
        ("selected", [2], "def selected():\n    return 2")
    ]
    corrupted = _missing_context(real_diff)
    refusal = _git(repo, "apply", "--reverse", "--check", "-", input=corrupted, check=False)
    assert refusal.returncode != 0
    with pytest.raises(ValueError, match="diff"):
        changed_functions(repo, corrupted)


def test_invalid_later_file_rejects_before_source_reads_and_execution(git_change, monkeypatch):
    repo, real_diff = git_change
    calls = []
    client = ScriptedModel(["must remain unused"])

    def forbidden(*args, **kwargs):
        calls.append("source-or-pytest")
        raise AssertionError("damaged diff reached source or test execution")

    monkeypatch.setattr("testpilot.diff.tokenize.open", forbidden)
    monkeypatch.setattr("testpilot.loop.run_pytest", forbidden)
    damaged = real_diff + HEADER.replace("sample.py", "other.py") + "@@ -1 +1 @@\n-old\n"
    with pytest.raises(ValueError, match="diff"):
        TestPilot(client).run(repo, damaged)
    assert calls == []
    assert client.calls == []


def _cli(repo, *args, stdin=None):
    env = _fixture_env()
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(ROOT))
    return subprocess.run(
        [sys.executable, "-B", "-m", "testpilot", *map(str, args)],
        cwd=repo.parent, env=env, input=stdin, capture_output=True, text=True, timeout=30,
    )


def test_native_targets_cli_refuses_damaged_stdin_without_success_json(git_change):
    repo, real_diff = git_change
    valid = _cli(repo, "targets", "--repo", repo, "--diff", "-", "--json", stdin=real_diff)
    assert valid.returncode == 0, valid.stderr
    assert len(json.loads(valid.stdout)["changed_functions"]) == 1
    invalid = _cli(repo, "targets", "--repo", repo, "--diff", "-", "--json",
                   stdin=_missing_context(real_diff))
    assert invalid.returncode == 2
    assert invalid.stdout == ""
    assert "testpilot: cannot inspect targets:" in invalid.stderr
    assert "diff" in invalid.stderr
    assert "Traceback" not in invalid.stderr


def test_native_run_cli_refuses_damaged_file_before_model_tests_or_output(git_change):
    repo, real_diff = git_change
    inputs = repo.parent / "script"
    inputs.mkdir()
    (inputs / "01_plan.md").write_text("Check selected returns two.\n", encoding="utf-8")
    fence = chr(96) * 3
    (inputs / "02_tests.md").write_text(
        fence + "python tests/test_selected.py\nfrom sample import selected\n"
        "def test_selected():\n    assert selected() == 2\n" + fence + "\n", encoding="utf-8")
    patch = repo.parent / "damaged.diff"
    patch.write_text(_missing_context(real_diff), encoding="utf-8")
    output = repo.parent / "result"
    run = _cli(repo, "run", "--repo", repo, "--diff", patch,
               "--backend", "scripted", "--script", inputs, "--rounds", 0, "--out", output)
    assert run.returncode == 2
    assert run.stdout == ""
    assert "testpilot: invalid diff format:" in run.stderr
    assert "Traceback" not in run.stderr
    assert not output.exists()
    assert (repo / "sample.py").read_text(encoding="utf-8") == "def selected():\n    return 2\n"


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_empty_context_and_no_newline_markers_preserve_complete_hunks(newline):
    diff_text = (
        HEADER + "@@ -1,3 +1,3 @@\n"
        " def selected():\n\n-    return 1\n\\ No newline at end of file\n"
        "+    return 2\n\\ No newline at end of file\n"
    ).replace("\n", newline)
    files = parse_unified_diff(diff_text)
    assert len(files) == 1
    assert files[0].added_lines == {3}
    assert files[0].touched_lines == {2, 3}


def test_valid_final_record_without_lf_is_counted_once():
    assert parse_unified_diff(VALID.rstrip("\n"))[0].added_lines == {2}


def test_new_deleted_and_zero_context_hunks_from_git(tmp_path):
    repo = tmp_path / "project"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "gone.py").write_text("def gone():\n    return 0\n", encoding="utf-8")
    (repo / "kept.py").write_text("def kept():\n    discard = 1\n    return 2\n", encoding="utf-8")
    _git(repo, "add", ".")
    (repo / "gone.py").unlink()
    (repo / "kept.py").write_text("def kept():\n    return 2\n", encoding="utf-8")
    (repo / "new.py").write_text('def fresh():\n    return "left\u2028right"', encoding="utf-8")
    _git(repo, "add", "-N", "new.py")
    diff_text = _git(repo, "diff", "--no-ext-diff", "--no-textconv", "--unified=0").stdout
    assert _git(repo, "apply", "--reverse", "--check", "--unidiff-zero", "-", input=diff_text).returncode == 0
    files = parse_unified_diff(diff_text)
    assert {f.path for f in files if f.is_deleted} == {"gone.py"}
    assert {f.path for f in files if f.is_new} == {"new.py"}
    selected = changed_functions(repo, diff_text)
    assert [(f.qualname, f.changed_lines) for f in selected] == [("kept", []), ("fresh", [1, 2])]


@pytest.mark.parametrize("range_field", [0, 1, 2, 3],
                         ids=["old-start", "old-count", "new-start", "new-count"])
def test_unsupported_hunk_integer_has_clean_parser_and_run_errors(git_change, monkeypatch, range_field):
    digit_limit = getattr(sys, "get_int_max_str_digits", lambda: 0)()
    if not digit_limit:
        pytest.skip("this runtime does not limit decimal integer conversion")
    monkeypatch.setenv("PYTHONINTMAXSTRDIGITS", str(digit_limit))
    repo, _ = git_change
    fields = ["1", "2", "1", "2"]
    fields[range_field] = "9" * (digit_limit + 1)
    header = f"@@ -{fields[0]},{fields[1]} +{fields[2]},{fields[3]} @@"
    damaged = VALID.replace("@@ -1,2 +1,2 @@", header)
    with pytest.raises(DiffFormatError, match="hunk range"):
        parse_unified_diff(damaged)
    script = repo.parent / "script"
    script.mkdir()
    (script / "01.md").write_text("Must remain unused.\n", encoding="utf-8")
    patch = repo.parent / "oversize.diff"
    patch.write_text(damaged, encoding="utf-8")
    output = repo.parent / "result"
    run = _cli(repo, "run", "--repo", repo, "--diff", patch,
               "--backend", "scripted", "--script", script, "--rounds", 0, "--out", output)
    assert run.returncode == 2
    assert run.stdout == ""
    assert "testpilot: invalid diff format:" in run.stderr
    assert "Traceback" not in run.stderr
    assert not output.exists()


def _mail_patch(repo, signature=None):
    identity = ("-c", "user.name=TestPilot fixture", "-c", "user.email=testpilot@example.invalid")
    _git(repo, *identity, "commit", "-qm", "Before change")
    _git(repo, "add", "sample.py")
    _git(repo, *identity, "commit", "-qm", "Change selected")
    version = _git(repo, "--version").stdout.removeprefix("git version ").strip()
    return _git(repo, "format-patch", "--stdout", "--no-stat",
                "--signature=" + (version if signature is None else signature), "-1").stdout


@pytest.fixture(params=[None, "HAMON Receiving Fixture"], ids=["git-version", "custom-text"])
def mail_change(git_change, request):
    repo, _ = git_change
    return repo, _mail_patch(repo, request.param)


def test_actual_git_mail_footer_preserves_complete_target_selection(mail_change):
    repo, patch = mail_change
    assert patch.startswith("From ") and "\n-- \n" in patch
    assert _git(repo, "apply", "--reverse", "--check", "-", input=patch).returncode == 0
    selected = changed_functions(repo, patch)
    assert [(f.qualname, f.changed_lines, f.source) for f in selected] == [
        ("selected", [2], "def selected():\n    return 2")
    ]


@pytest.mark.parametrize("missing", ["old", "new", "both", "later-file", "after-footer"])
def test_git_mail_footer_never_completes_a_missing_body_record(mail_change, missing):
    _, patch = mail_change
    if missing == "later-file":
        body, footer = patch.rsplit("\n-- \n", 1)
        patch = body + "\n" + HEADER.replace("sample.py", "other.py") + "@@ -1 +1 @@\n-old\n-- \n" + footer
    elif missing == "after-footer":
        patch += HEADER.replace("sample.py", "other.py") + "@@ -1 +1 @@\n-old\n"
    else:
        old_count = 3 if missing in ("old", "both") else 2
        new_count = 3 if missing in ("new", "both") else 2
        patch = patch.replace("@@ -1,2 +1,2 @@", f"@@ -1,{old_count} +1,{new_count} @@")
    with pytest.raises(DiffFormatError, match="diff"):
        parse_unified_diff(patch)


def test_mail_can_delete_source_text_shaped_like_the_signature_delimiter(git_change):
    repo, _ = git_change
    source = repo / "sample.py"
    source.write_text("def selected():\n    return '''before\n- \nafter'''\n", encoding="utf-8")
    _git(repo, "add", "sample.py")
    source.write_text("def selected():\n    return '''after'''\n", encoding="utf-8")
    patch = _mail_patch(repo)
    assert patch.count("\n-- \n") == 2
    assert _git(repo, "apply", "--reverse", "--check", "-", input=patch).returncode == 0
    selected = changed_functions(repo, patch)
    assert [(f.qualname, f.changed_lines, f.source) for f in selected] == [
        ("selected", [2], "def selected():\n    return '''after'''")
    ]


@pytest.mark.parametrize("existing_output", [False, True])
def test_native_diff_error_precedes_model_config_and_preserves_output(git_change, existing_output):
    repo, real_diff = git_change
    patch = repo.parent / "damaged.diff"
    patch.write_text(_missing_context(real_diff), encoding="utf-8")
    output = repo.parent / "result"
    retained = {}
    if existing_output:
        output.mkdir()
        for name in ("report.json", "report.html", "report.md", "testpilot.patch"):
            content = ("retain original " + name + "\n").encode("utf-8")
            (output / name).write_bytes(content)
            retained[name] = content
    run = _cli(repo, "run", "--repo", repo, "--diff", patch, "--backend", "scripted",
               "--script", repo.parent / "missing-model-config", "--rounds", 0, "--out", output)
    assert run.returncode == 2
    assert run.stdout == ""
    assert "testpilot: invalid diff format:" in run.stderr
    assert "Traceback" not in run.stderr
    if existing_output:
        assert {p.name: p.read_bytes() for p in output.iterdir()} == retained
    else:
        assert not output.exists()
