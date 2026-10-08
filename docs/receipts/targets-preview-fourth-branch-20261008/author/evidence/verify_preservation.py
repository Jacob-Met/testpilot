"""Verify the three-path preview addition and reconstruct its patch with Git."""
from __future__ import annotations
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PATHS = ("testpilot/__main__.py", "tests/test_cli_targets.py", "docs/targets-preview.md")

def pin(path):
    raw = path.read_bytes()
    return {"git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}

def function_text(source, name):
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(source, node)

def main():
    before, after = ROOT / "baseline", ROOT / "candidate"
    original = (before / PATHS[0]).read_text()
    current = (after / PATHS[0]).read_text()
    run_start = '    if a.diff == "-":'
    tail_equal = original[original.index(run_start):] == current[current.index(run_start):]
    python_equal = function_text(original, "_python_executable") == function_text(current, "_python_executable")
    original_main = next(n for n in ast.parse(original).body if isinstance(n, ast.FunctionDef) and n.name == "main")
    current_main = next(n for n in ast.parse(current).body if isinstance(n, ast.FunctionDef) and n.name == "main")
    # Statements before parse_args are unchanged after removing only the new preview parser.
    first_preview = next(i for i, n in enumerate(current_main.body)
                         if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "preview" for t in n.targets))
    original_parser = original_main.body[:first_preview]
    parser_equal = ast.dump(ast.Module(original_parser, []), include_attributes=False) == ast.dump(
        ast.Module(current_main.body[:first_preview], []), include_attributes=False)
    preserved = {str(p.relative_to(before)): pin(p) for p in before.rglob("*")
                 if p.is_file() and str(p.relative_to(before)) != PATHS[0]}
    for path, expected in preserved.items():
        if pin(after / path) != expected:
            raise RuntimeError("changed support: " + path)
    originals = {str(p.relative_to(before)) for p in before.rglob("*") if p.is_file()}
    candidates = {str(p.relative_to(after)) for p in after.rglob("*") if p.is_file()}
    additions = sorted(candidates - originals)
    changes = sorted(p for p in originals & candidates if (before / p).read_bytes() != (after / p).read_bytes())
    if not (tail_equal and python_equal and parser_equal and
            additions == sorted(PATHS[1:]) and changes == [PATHS[0]] and not originals - candidates):
        raise RuntimeError((tail_equal, python_equal, parser_equal, additions, changes))
    env = {"PATH": os.defpath, "LANG": "C.UTF-8",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    def git(root, *args, input=None):
        return subprocess.run(["git", "-C", str(root), *args], input=input,
                              check=True, capture_output=True, env=env).stdout
    with tempfile.TemporaryDirectory(prefix="patch-rebuild-", dir=ROOT) as td:
        source = Path(td) / "source"
        receiver = Path(td) / "receiver"
        shutil.copytree(before, source)
        git(source, "init", "-q")
        git(source, "add", ".")
        for path in PATHS:
            dest = source / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((after / path).read_bytes())
        git(source, "add", "-N", "--", *PATHS[1:])
        patch = git(source, "diff", "--binary", "--no-ext-diff", "--no-textconv")
        patch_path = ROOT / "candidate.patch"
        patch_path.write_bytes(patch)
        shutil.copytree(before, receiver)
        git(receiver, "init", "-q")
        git(receiver, "apply", "--check", str(patch_path))
        git(receiver, "apply", str(patch_path))
        recreated = {p: pin(receiver / p) for p in PATHS}
        if recreated != {p: pin(after / p) for p in PATHS}:
            raise RuntimeError("Git reconstruction differs")
        if any(pin(receiver / p) != value for p, value in preserved.items()):
            raise RuntimeError("Git reconstruction changed support")
    result = {
        "run_tail_byte_identical": tail_equal,
        "run_parser_statements_identical": parser_equal,
        "python_executable_helper_byte_identical": python_equal,
        "preserved_support": preserved,
        "changed_paths": changes, "new_paths": additions, "removed_paths": [],
        "candidate_paths": {p: pin(after / p) for p in PATHS},
        "patch": pin(ROOT / "candidate.patch"),
        "git_apply_check_exit": 0,
        "actual_git_reconstruction_exact": True,
    }
    (ROOT / "evidence/preservation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ("preserved_support", "candidate_paths")}))
    return result

if __name__ == "__main__":
    main()
