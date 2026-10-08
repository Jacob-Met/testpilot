"""Independent real-Git byte-path receiving challenge; pass diff.py as argv[1]."""
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path


source = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("independent_testpilot_diff", source)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory(prefix="testpilot-real-git-independent-") as td:
    root = Path(td)
    expected = []
    for value in range(1, 256):
        if value == 47:
            continue
        name = os.fsdecode(b"file_" + bytes([value]) + b".py")
        (root / name).write_text("def selected():\n    return 1\n", encoding="utf-8")
        expected.append(name)

    def git(*args):
        return subprocess.run(
            ["git", "-C", td, "-c", "core.hooksPath=/dev/null", *args],
            check=True, capture_output=True,
        ).stdout

    git("init", "-q")
    git("add", "--all", "--")
    patch = git("-c", "core.quotePath=true", "diff", "--cached", "--no-ext-diff", "--").decode("utf-8")
    changes = module.parse_unified_diff(patch)
    selected = module.changed_functions(root, patch)
    expected_bytes = {os.fsencode(path) for path in expected}
    parsed_exact = {os.fsencode(item.path) for item in changes} == expected_bytes
    selected_exact = {os.fsencode(item.path) for item in selected} == expected_bytes
    line_identity = all(item.qualname == "selected" and item.changed_lines == [1, 2] for item in selected)
    result = {
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "python": platform.python_version(),
        "git": git("--version").decode("utf-8").strip(),
        "platform": platform.platform(),
        "challenge": "all nonzero single POSIX filename bytes except slash, via actual staged Git diff",
        "core_quotePath": True,
        "expected_paths": len(expected),
        "parsed_paths": len(changes),
        "selected_functions": len(selected),
        "parsed_raw_bytes_exact": parsed_exact,
        "selected_raw_bytes_exact": selected_exact,
        "function_and_added_line_identity": line_identity,
        "skips": 0,
        "passed": parsed_exact and selected_exact and line_identity,
    }
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(1)
