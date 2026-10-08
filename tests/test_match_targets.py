"""Actual Git/AST/pytest receiving controls for match-branch callables."""
from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

import pytest

from testpilot.diff import changed_functions, parse_unified_diff
from testpilot.loop import TestPilot
from testpilot.model import RoutingConfig, ScriptedModel


SOURCE = """BACKEND = "basic"
match BACKEND:
    case "basic":
        def total(items):
            return sum(items) + 1
    case _:
        def fallback(items):
            return sum(items)
"""


def git_change(repo: Path, before: str | None, after: str | None, path="backend.py"):
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if before is not None:
        target.write_text(before, encoding="utf-8")
        subprocess.run(["git", "add", "--", path], cwd=repo, check=True)
    if after is None:
        target.unlink()
    else:
        target.write_text(after, encoding="utf-8")
        if before is None:
            subprocess.run(["git", "add", "--intent-to-add", "--", path],
                           cwd=repo, check=True)
    diff = subprocess.check_output(
        ["git", "-c", "color.ui=false", "diff", "--no-ext-diff", "--unified=0", "--", path],
        cwd=repo, text=True)
    return target, diff


def test_changed_match_branch_has_exact_public_target(tmp_path):
    after = SOURCE.replace("sum(items) + 1", "sum(items) + 2")
    _, diff = git_change(tmp_path, SOURCE, after)
    parsed = parse_unified_diff(diff)
    assert parsed[0].added_lines == {5}
    targets = changed_functions(tmp_path, diff)
    assert [target.qualname for target in targets] == ["total"]
    target = targets[0]
    assert target.path == "backend.py" and target.module == "backend"
    assert target.import_name == "total" and not target.is_method
    assert (target.lineno, target.end_lineno, target.changed_lines) == (4, 5, [5])
    assert target.source == "        def total(items):\n            return sum(items) + 2"


def test_decorated_async_match_method_retains_class_identity(tmp_path):
    before = """class Backend:
    match "async":
        case "async":
            @classmethod
            async def total(cls, items):
                return sum(items) + 1
"""
    after = before.replace("sum(items) + 1", "sum(items) + 2")
    _, diff = git_change(tmp_path, before, after, "src/pkg/backend.py")
    targets = changed_functions(tmp_path, diff)
    assert len(targets) == 1
    target = targets[0]
    assert (target.qualname, target.module, target.import_name) == (
        "Backend.total", "pkg.backend", "Backend")
    assert target.is_method
    assert (target.lineno, target.end_lineno, target.changed_lines) == (4, 6, [6])
    assert target.source.startswith("            @classmethod\n")
    assert "async def total" in target.source


@pytest.mark.parametrize("wrapper", ["if", "try", "with", "match"])
def test_nested_branch_containers_reach_only_changed_callable(tmp_path, wrapper):
    block = """match "inner":
    case "inner":
        def chosen():
            return 1
    case _:
        def untouched():
            return 9
"""
    indented = textwrap.indent(block, "    ")
    if wrapper == "if":
        before = "if True:\n" + indented
    elif wrapper == "try":
        before = "try:\n" + indented + "finally:\n    pass\n"
    elif wrapper == "with":
        before = "with __import__('contextlib').nullcontext():\n" + indented
    else:
        before = "match 'outer':\n    case 'outer':\n" + textwrap.indent(block, "        ")
    after = before.replace("return 1", "return 2")
    _, diff = git_change(tmp_path, before, after)
    targets = changed_functions(tmp_path, diff)
    assert [target.qualname for target in targets] == ["chosen"]
    assert len(targets[0].changed_lines) == 1
    assert "return 2" in targets[0].source


def test_pure_deletion_in_match_branch_selects_surviving_callable(tmp_path):
    before = SOURCE.replace("            return sum(items) + 1",
                            "            ignored = 7\n            return sum(items) + 1")
    _, diff = git_change(tmp_path, before, SOURCE)
    targets = changed_functions(tmp_path, diff)
    assert [target.qualname for target in targets] == ["total"]
    assert targets[0].changed_lines == []
    assert "ignored" not in targets[0].source


def test_match_inside_function_keeps_enclosing_function_attribution(tmp_path):
    before = """def enclosing(choice):
    match choice:
        case "a":
            def nested():
                return 1
            return nested()
        case _:
            return 0
"""
    after = before.replace("return 1", "return 2")
    _, diff = git_change(tmp_path, before, after)
    targets = changed_functions(tmp_path, diff)
    assert [target.qualname for target in targets] == ["enclosing"]
    assert targets[0].changed_lines == [5]
    assert "def nested" in targets[0].source


def test_selection_does_not_execute_match_subject_or_guard(tmp_path):
    before = """def must_not_run():
    raise AssertionError("source inspection executed code")

match must_not_run():
    case value if must_not_run():
        def chosen():
            return 1
"""
    after = before.replace("return 1", "return 2")
    _, diff = git_change(tmp_path, before, after)
    targets = changed_functions(tmp_path, diff)
    assert [target.qualname for target in targets] == ["chosen"]


def test_new_and_deleted_match_source_keep_diff_semantics(tmp_path):
    source = """match "a":
    case "a":
        def selected():
            return 1
"""
    _, diff = git_change(tmp_path, None, source)
    assert parse_unified_diff(diff)[0].is_new
    assert [target.qualname for target in changed_functions(tmp_path, diff)] == ["selected"]
    # A separate actual index snapshot gives a genuine deleted-file diff.
    subprocess.run(["git", "add", "--", "backend.py"], cwd=tmp_path, check=True)
    (tmp_path / "backend.py").unlink()
    deleted = subprocess.check_output(["git", "diff", "--", "backend.py"],
                                      cwd=tmp_path, text=True)
    assert parse_unified_diff(deleted)[0].is_deleted
    assert changed_functions(tmp_path, deleted) == []


def test_actual_pipeline_generates_tests_for_match_callable(tmp_path):
    after = SOURCE.replace("sum(items) + 1", "sum(items) + 2")
    target, diff = git_change(tmp_path, SOURCE, after)
    original = target.read_bytes()
    client = ScriptedModel([
        "Check the active basic backend total on positive and empty inputs.",
        "```python path=tests/test_backend.py\n"
        "from backend import total\n\n"
        "def test_total():\n    assert total([1, 2]) == 5\n\n"
        "def test_empty():\n    assert total([]) == 2\n```",
    ])
    report = TestPilot(client, RoutingConfig(planner_model="P", editor_model="E"),
                       coverage=False, timeout_s=30, max_repair_rounds=0).run(tmp_path, diff)
    assert report.status == "passed"
    assert report.tests_written == 2 and report.final["passed"] == 2
    assert [item["qualname"] for item in report.changed_functions] == ["total"]
    assert [call[0] for call in client.calls] == ["P", "E"]
    assert "def total" in client.calls[0][1][1]["content"]
    assert "+++ b/tests/test_backend.py" in report.patch
    assert target.read_bytes() == original
    assert not (tmp_path / "tests").exists()
    patch = tmp_path / "generated.patch"
    patch.write_text(report.patch, encoding="utf-8")
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=tmp_path, check=True)
