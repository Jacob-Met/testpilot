"""Bind automatic targets to the source the sandbox can actually import."""
import json
import stat
import sys
from pathlib import Path

import pytest

from testpilot.diff import changed_functions
from testpilot.sandbox import _run, clean_env, run_pytest


_SELECTED_SOURCE = "def selected_value():\n    return 23\n"
_NAME = "_identity_pricing"


def _snapshot(root):
    return {
        path.relative_to(root).as_posix(): (
            path.read_bytes(), stat.S_IMODE(path.stat().st_mode)
        )
        for path in root.rglob("*") if path.is_file()
    }


def _project(root, relative, namesake=False):
    root.mkdir()
    selected = root / relative
    selected.parent.mkdir(parents=True, exist_ok=True)
    parent = selected.parent
    while parent != root:
        if parent.name != "src":
            (parent / "__init__.py").write_text("", encoding="utf-8")
        parent = parent.parent
    selected.write_text(_SELECTED_SOURCE, encoding="utf-8")
    if namesake:
        (root / f"{_NAME}.py").write_text(
            "def selected_value():\n    return 99\n", encoding="utf-8"
        )
    return _snapshot(root)


def _select(root, relative):
    patch = (
        f"--- a/{relative}\n+++ b/{relative}\n"
        "@@ -1,2 +1,2 @@\n def selected_value():\n"
        "-    return 22\n+    return 23\n"
    )
    targets = changed_functions(root, patch)
    assert len(targets) == 1
    target = targets[0]
    assert (target.path, target.qualname, target.changed_lines, target.source) == (
        relative, "selected_value", [2], _SELECTED_SOURCE.rstrip("\n")
    )
    return target


@pytest.mark.parametrize(
    ("relative", "expected_module", "namesake"),
    [
        (f"{_NAME}.py", _NAME, False),
        (f"pkg/{_NAME}.py", f"pkg.{_NAME}", False),
        (f"src/pkg/{_NAME}.py", f"pkg.{_NAME}", False),
        (f"src/lib/{_NAME}.py", f"lib.{_NAME}", False),
        (f"lib/{_NAME}.py", f"lib.{_NAME}", False),
        (f"lib/{_NAME}.py", f"lib.{_NAME}", True),
        ("lib/__init__.py", "lib", False),
    ],
    ids=["root-module", "root-package", "src-package", "src-lib",
         "lib-package", "lib-with-root-namesake", "lib-init"],
)
def test_selected_module_imports_the_selected_source(
    tmp_path, relative, expected_module, namesake
):
    repo = tmp_path / "repo"
    before = _project(repo, relative, namesake)
    try:
        target = _select(repo, relative)
        command = (
            "import importlib,json; from pathlib import Path; "
            f"module=importlib.import_module({target.module!r}); "
            "print(json.dumps({'path':str(Path(module.__file__).resolve()),"
            "'value':module.selected_value()}))"
        )
        rc, output, timed_out = _run(
            [sys.executable, "-c", command], repo, clean_env(repo), 10
        )
        assert not timed_out, output
        assert rc == 0, output
        observed = json.loads(output)
        assert observed == {"path": str((repo / relative).resolve()), "value": 23}
        assert target.module == expected_module
    finally:
        assert _snapshot(repo) == before


@pytest.mark.parametrize("relative", [f"lib/{_NAME}.py", f"src/lib/{_NAME}.py"],
                         ids=["lib-with-root-namesake", "src-lib"])
def test_generated_tests_run_against_selected_module(tmp_path, relative):
    repo = tmp_path / "repo"
    before = _project(repo, relative, namesake=relative.startswith("lib/"))
    try:
        target = _select(repo, relative)
        generated = (
            "from pathlib import Path\n"
            f"import {target.module} as selected\n\n"
            "def test_selected_source_and_behavior():\n"
            "    assert selected.selected_value() == 23\n"
            "    assert Path(selected.__file__).resolve() == "
            f"(Path.cwd() / {relative!r}).resolve()\n"
        )
        result = run_pytest(
            repo, {"tests/test_selected_identity.py": generated},
            timeout=20, python=sys.executable, coverage=False,
        )
        assert result.ok, result.failure_report()
        assert result.returncode == 0 and result.junit_available
        assert result.generated_counts() == {
            "collected": 1, "passed": 1, "failed": 0, "error": 0, "skipped": 0
        }
    finally:
        assert _snapshot(repo) == before
