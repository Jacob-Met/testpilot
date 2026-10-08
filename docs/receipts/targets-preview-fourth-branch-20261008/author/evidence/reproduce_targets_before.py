"""Reproduce the missing target-preview CLI on exact native TestPilot source.

Use a real disposable Git diff and the existing public selector as the control.
No model, pytest, project module import, network, or user repository is used.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "baseline"

def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def command(argv, *, cwd, env=None):
    p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=15)
    return {"argv": [str(x) for x in argv], "returncode": p.returncode,
            "stdout": p.stdout, "stderr": p.stderr}

def main():
    # Git's author settings are command-local and the worktree is private.
    env = {"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1",
           "TESTPILOT_BACKEND": "scripted", "LANG": "C.UTF-8"}
    with tempfile.TemporaryDirectory(prefix="testpilot-targets-before-", dir=ROOT) as td:
        repo = Path(td)
        source = repo / "subject.py"
        original = (
            'raise RuntimeError("selection must not execute project source")\n\n'
            "def untouched():\n    return 4\n\n"
            "def increment(value):\n    return value + 1\n"
        )
        source.write_text(original, encoding="utf-8")
        setup = [
            command(["git", "init", "-q"], cwd=repo, env=env),
            command(["git", "add", "subject.py"], cwd=repo, env=env),
            command(["git", "-c", "user.name=TestPilot Fixture",
                     "-c", "user.email=testpilot-fixture@invalid.local",
                     "-c", "commit.gpgsign=false",
                     "commit", "-q", "-m", "before"], cwd=repo, env=env),
        ]
        if any(x["returncode"] for x in setup):
            raise RuntimeError(setup)
        source.write_text(original.replace("value + 1", "value + 2"), encoding="utf-8")
        before = file_hash(source)
        diff = command(["git", "diff", "HEAD", "--", "*.py"], cwd=repo, env=env)
        if diff["returncode"] or not diff["stdout"]:
            raise RuntimeError(diff)
        sys.path.insert(0, str(SOURCE))
        from testpilot.diff import changed_functions
        selected = [f.to_dict() for f in changed_functions(repo, diff["stdout"])]
        preview = command([sys.executable, "-B", "-m", "testpilot", "targets",
                           "--repo", str(repo), "--git-base", "HEAD", "--json"],
                          cwd=SOURCE, env=env)
        existing_run = command([sys.executable, "-B", "-m", "testpilot", "run",
                                "--repo", str(repo), "--git-base", "HEAD"],
                               cwd=SOURCE, env=env)
        result = {
            "source_pin": json.loads((ROOT / "evidence/source-pins.json").read_text()),
            "consumer": "actual native parser and existing changed_functions public API",
            "git_diff": diff["stdout"],
            "native_selector": selected,
            "targets_cli": preview,
            "existing_run_without_model_configuration": existing_run,
            "source_unchanged": before == file_hash(source),
            "source_import_tripwire": "not executed (selector parsed source with top-level raise)",
            "setup_count": len(setup),
            "conclusion": "Existing native selector selects increment; targets CLI is unavailable.",
            "limitations": "Missing capability, not a regression or false-green result. No pytest/provider execution.",
        }
        if len(selected) != 1 or selected[0]["qualname"] != "increment":
            raise RuntimeError(result)
        if preview["returncode"] != 2 or "invalid choice: 'targets'" not in preview["stderr"]:
            raise RuntimeError(result)
        if existing_run["returncode"] != 2 or not result["source_unchanged"]:
            raise RuntimeError(result)
        target = ROOT / "evidence/baseline-targets.json"
        target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"native_functions": len(selected),
                          "native_qualname": selected[0]["qualname"],
                          "targets_exit": preview["returncode"],
                          "existing_run_exit": existing_run["returncode"],
                          "source_unchanged": result["source_unchanged"],
                          "receipt": str(target)}))

if __name__ == "__main__":
    main()
