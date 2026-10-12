"""Complete-record controls for dense and sparse changed-line selection."""
from __future__ import annotations

import ast
import json
import subprocess
import sys

import pytest

from testpilot.diff import functions_touching


SOURCE = (
    "raise RuntimeError('selection must not execute source')\n"
    "@decorate(\n"
    "    option=True,\n"
    ")\n"
    "async def outer():\n"
    "    def nested():\n"
    "        return 'left\u2028right'\n"
    "    return nested()\n"
    "\n"
    "class Box:\n"
    "    @staticmethod\n"
    "    def read():\n"
    "        return 3\n"
    "\n"
    "if enabled:\n"
    "    def branch():\n"
    "        return 4\n"
    "else:\n"
    "    def branch():\n"
    "        return 5\n"
    "\n"
    "def untouched():\n"
    "    return 6\n"
)

# These spans and names are literal fixture expectations, not read from the AST.
SPANS = [
    ("outer", 2, 8, False),
    ("Box.read", 11, 13, True),
    ("branch", 16, 17, False),
    ("branch", 19, 20, False),
    ("untouched", 22, 23, False),
]


def expected_records(source, touched, added):
    physical = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    records = []
    for name, start, end, method in SPANS:
        span = set(range(start, end + 1))
        if touched & span:
            records.append({
                "path": "src/pkg/example.py",
                "module": "pkg.example",
                "qualname": name,
                "lineno": start,
                "end_lineno": end,
                "changed_lines": sorted(added & span),
                "source": "\n".join(physical[start - 1:end]),
                "is_method": method,
            })
    return records


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_dense_sparse_and_boundary_sets_preserve_complete_records(newline):
    source = SOURCE.replace("\n", newline)
    cases = [
        (set(), set(range(1, 30))),
        ({-100, 0, 1, 9, 10, 14, 15, 18, 21, 24, 10**30}, {2, 12}),
        ({2, 11, 16, 19, 22}, {8, 13, 17, 20, 23}),
        ({8, 13, 17, 20, 23}, {2, 11, 16, 19, 22}),
        ({7}, {7}),  # Nested definitions belong to the containing callable.
        ({12}, set()),  # A pure deletion still selects the surviving method.
        (set(range(-5, 32)), set(range(-5, 32))),
    ]
    for touched, added in cases:
        before = (touched.copy(), added.copy())
        actual = [item.to_dict() for item in functions_touching(
            source, "src/pkg/example.py", touched, added)]
        assert actual == expected_records(source, touched, added)
        assert (touched, added) == before


def test_every_single_line_and_changed_subset_preserves_literal_spans():
    additions = [{2, 3, 7, 8, 10, 11, 13, 16, 17, 19, 20, 22, 23}, set()]
    for line in range(-1, 27):
        for added in additions:
            touched = {line}
            actual = [item.to_dict() for item in functions_touching(
                SOURCE, "src/pkg/example.py", touched, added)]
            assert actual == expected_records(SOURCE, touched, added)


def test_empty_selection_keeps_syntax_error_and_no_callable_behavior():
    with pytest.raises(SyntaxError):
        functions_touching("def broken(:\n", "bad.py", set(), set())
    assert functions_touching("x = 1\n", "value.py", {1}, {1}) == []
    assert functions_touching("", "empty.py", set(), set()) == []
    # The fixture remains syntactically inspectable without importing it.
    ast.parse(SOURCE)


def test_actual_targets_cli_preserves_dense_file_records(tmp_path):
    count = 160
    source = "".join(f"def f_{i}():\n    return {i}\n\n" for i in range(count))
    path = tmp_path / "many.py"
    path.write_text(source, encoding="utf-8")
    diff = tmp_path / "new.diff"
    lines = source.splitlines()
    diff.write_text("--- /dev/null\n+++ b/many.py\n"
                    f"@@ -0,0 +1,{len(lines)} @@\n"
                    + "".join("+" + line + "\n" for line in lines), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-B", "-m", "testpilot", "targets", "--repo", str(tmp_path),
         "--diff", str(diff), "--json"], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    expected = [{
        "path": "many.py", "module": "many", "qualname": f"f_{i}",
        "lineno": 3 * i + 1, "end_lineno": 3 * i + 2,
        "changed_lines": [3 * i + 1, 3 * i + 2],
        "source": f"def f_{i}():\n    return {i}", "is_method": False,
    } for i in range(count)]
    assert json.loads(result.stdout) == {"changed_functions": expected}
    assert path.read_text(encoding="utf-8") == source
