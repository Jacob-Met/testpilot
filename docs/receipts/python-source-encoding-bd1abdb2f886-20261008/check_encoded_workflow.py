"""Receive real encoded-source Git edits through the public TestPilot CLI."""
from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", *args],
        cwd=repo, check=True, capture_output=True, timeout=10,
    ).stdout


def body(offset: int) -> str:
    return (
        'def price():\n    """Return the café price."""\n'
        "    total = 0\n    total += 1\n    total += 2\n    total += 3\n"
        f"    total += 4\n    total += 5\n    return total + {offset}\n"
    )


def receive(source: Path, case: str) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"encoded-{case}-") as location:
        work = Path(location)
        repo = work / "project"
        (repo / "tests").mkdir(parents=True)
        prefix, encoding = ((codecs.BOM_UTF8, "utf-8") if case == "utf8_bom" else
                            (b"#!/usr/bin/env python\n# coding: latin-1\n", "latin-1"))
        module = repo / "price.py"
        existing = repo / "tests/test_existing.py"
        existing.write_text(
            "from price import price\ndef test_existing():\n    assert price.__name__ == 'price'\n",
            encoding="utf-8",
        )
        git(repo, "init", "-q")
        module.write_bytes(prefix + body(1).encode(encoding))
        git(repo, "add", ".")
        git(repo, "-c", "user.name=Encoded workflow", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "original")
        module.write_bytes(prefix + body(2).encode(encoding))
        patch = work / "change.diff"
        diff = git(repo, "diff", "--no-ext-diff", "--no-textconv", "--unified=3")
        diff.decode("utf-8")  # The existing CLI's UTF-8 diff transport is sufficient.
        patch.write_bytes(diff)
        script = work / "script"
        script.mkdir()
        (script / "01_plan.md").write_text("Check the updated café price and its docstring.\n", encoding="utf-8")
        (script / "02_tests.md").write_text(
            "```python path=tests/test_encoded_price.py\n"
            "from price import price\n\ndef test_price():\n"
            "    assert price() == 17\n    assert 'café' in price.__doc__\n```\n",
            encoding="utf-8",
        )
        originals = {str(path.relative_to(repo)): sha(path.read_bytes()) for path in (module, existing)}
        imported = subprocess.run(
            [sys.executable, "-B", "-c", "import price; print(price.price())"],
            cwd=repo, capture_output=True, text=True, timeout=10,
        )
        assert imported.returncode == 0 and imported.stdout == "17\n", imported.stderr
        out = work / "output"
        command = [sys.executable, "-m", "testpilot", "run", "--repo", str(repo),
                   "--diff", str(patch), "--script", str(script), "--backend", "scripted",
                   "--python", sys.executable, "--rounds", "0", "--timeout", "10", "--out", str(out)]
        env = dict(os.environ, PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE="1")
        for name in list(env):
            if name.startswith("TESTPILOT_"):
                env.pop(name)
        run = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True, timeout=35)
        unchanged = originals == {str(path.relative_to(repo)): sha(path.read_bytes()) for path in (module, existing)}
        assert unchanged
        result = {
            "case": case, "command": command, "exit_code": run.returncode,
            "stdout": run.stdout, "stderr": run.stderr,
            "actual_python_import": 17, "diff_valid_utf8": True,
            "source_sha256": originals["price.py"], "existing_test_sha256": originals["tests/test_existing.py"],
            "git_diff_sha256": sha(diff), "git_diff": diff.decode("utf-8"),
            "original_files_unchanged": unchanged,
            "generated_file_absent_from_input": not (repo / "tests/test_encoded_price.py").exists(),
        }
        assert result["generated_file_absent_from_input"]
        if (out / "report.json").is_file():
            report = json.loads((out / "report.json").read_bytes())
            result["report"] = report
            subprocess.run(["git", "apply", "--check", str(out / "testpilot.patch")],
                           cwd=repo, check=True, capture_output=True, timeout=10)
            result["git_apply_check"] = True
            result["patch"] = (out / "testpilot.patch").read_text(encoding="utf-8")
            result["markdown_written"] = (out / "report.md").is_file()
            assert run.returncode == 0 and report["status"] == "passed"
            assert report["tests_written"] == 1 and report["repair_rounds_used"] == 0
            assert report["final"]["passed"] == 2 and report["final"]["failed"] == 0
            assert len(report["ledger"]["entries"]) == 2
            assert report["changed_functions"][0]["source"] == body(2).rstrip("\n")
            assert report["coverage"]["changed_lines_before"] == 0.0
            assert report["coverage"]["changed_lines_after"] == 100.0
        else:
            assert run.returncode != 0
            assert "SyntaxError" in run.stderr or "UnicodeDecodeError" in run.stderr
            result["report"] = None
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    results = [receive(source, case) for case in ("utf8_bom", "latin1_cookie")]
    receipt = {
        "driver_sha256": sha(Path(__file__).read_bytes()),
        "runtime_sha256": sha((source / "testpilot/diff.py").read_bytes()),
        "python": sys.version, "platform": platform.platform(),
        "git": subprocess.check_output(["git", "--version"], text=True).strip(),
        "cases": results,
    }
    args.output.write_text(json.dumps(receipt, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "cases": [
        {"case": item["case"], "exit_code": item["exit_code"],
         "status": item["report"]["status"] if item["report"] else "source_error"}
        for item in results]}))


if __name__ == "__main__":
    main()
