"""Separate macOS native receiving for explicit CLI coverage choice.

This is not a replay or receipt of the unknown-outcome ThinkPad probe.
The authored optional coverage plugin fails; its project tests are independent.
"""
from __future__ import annotations
import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "baseline-f3b2135c"
EVIDENCE = ROOT / "macos-baseline-receiving"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def snapshot(root):
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and ".git" not in path.relative_to(root).parts:
            result[str(path.relative_to(root))] = {
                "sha256": digest(path.read_bytes()), "bytes": path.stat().st_size,
                "mode": oct(path.stat().st_mode & 0o777),
            }
    return result

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

def environment(case):
    tmp = case / "temporary"
    tmp.mkdir()
    return {
        "PATH": os.defpath,
        "PYTHONPATH": str(SOURCE),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "TMPDIR": str(tmp),
        "LC_ALL": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
    }

def author_project(case, instrumentation_error):
    repo = case / "project"
    (repo / "tests").mkdir(parents=True)
    filename_bytes = b"subject.py"
    filename = os.fsdecode(filename_bytes)
    subject = repo / filename
    subject.write_text("def step(value):\n    return value + 6\n", encoding="utf-8")
    import_code = (
        "import importlib.util\nimport os\nfrom pathlib import Path\n"
        f"_path = Path(__file__).resolve().parents[1] / os.fsdecode({filename_bytes!r})\n"
        "_spec = importlib.util.spec_from_file_location('fixture_subject', _path)\n"
        "_subject = importlib.util.module_from_spec(_spec)\n"
        "_spec.loader.exec_module(_subject)\n"
    )
    (repo / "tests/test_existing.py").write_text(
        import_code + "\ndef test_existing_value():\n    assert _subject.step(3) == 10\n", encoding="utf-8"
    )
    (repo / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n', encoding="utf-8"
    )
    if instrumentation_error:
        (repo / ".coveragerc").write_text("[run]\nplugins = authored_coverage_failure\n", encoding="utf-8")
        (repo / "authored_coverage_failure.py").write_text(
            "def coverage_init(reg, options):\n"
            "    raise RuntimeError('authored optional coverage plugin cannot initialize')\n",
            encoding="utf-8",
        )
    git = shutil.which("git")
    assert git, "git is required to author this fixture"
    git_env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
    def git_call(*args):
        return subprocess.run(
            [git, "-C", str(repo), "-c", "core.hooksPath=/dev/null", *args],
            env=git_env, capture_output=True, check=True,
        )
    git_call("init", "--quiet")
    git_call("add", "--", ".")
    git_call("-c", "user.name=TestPilot fixture", "-c", "user.email=fixture@example.invalid",
             "commit", "--quiet", "-m", "authored fixture")
    subject.write_text("def step(value):\n    return value + 7\n", encoding="utf-8")
    diff = git_call("diff", "--no-ext-diff", "--no-color", "HEAD", "--", "*.py").stdout
    (case / "change.diff").write_bytes(diff)
    replies = case / "replies"
    replies.mkdir()
    (replies / "00.md").write_text("Test the changed step return with an independent input.\n", encoding="utf-8")
    generated = import_code + "\ndef test_generated_value():\n    assert _subject.step(5) == 12\n"
    fence = chr(96) * 3
    (replies / "01.md").write_text(
        fence + "python path=tests/test_generated_coverage_choice.py\n" + generated + fence + "\n",
        encoding="utf-8",
    )
    return repo, replies, diff

def cli_case(label, *, instrumentation_error, disable):
    case = EVIDENCE / label
    case.mkdir()
    repo, replies, diff = author_project(case, instrumentation_error)
    before = snapshot(repo)
    command = [
        sys.executable, "-B", "-m", "testpilot", "run",
        "--repo", str(repo), "--diff", str(case / "change.diff"),
        "--backend", "scripted", "--script", str(replies), "--rounds", "0",
        "--timeout", "15", "--python", sys.executable, "--out", str(case / "out"),
    ]
    if disable:
        command.append("--no-coverage")
    env = environment(case)
    started = time.monotonic()
    completed = subprocess.run(command, cwd=case, env=env, capture_output=True, timeout=55)
    (case / "stdout.log").write_bytes(completed.stdout)
    (case / "stderr.log").write_bytes(completed.stderr)
    report_path = case / "out/report.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else None
    receipt = {
        "label": label, "command": command, "elapsed_seconds": time.monotonic() - started,
        "returncode": completed.returncode,
        "stdout": completed.stdout.decode("utf-8", "backslashreplace"),
        "stderr": completed.stderr.decode("utf-8", "backslashreplace"),
        "report": report, "input_before": before, "input_after": snapshot(repo),
        "input_unchanged": before == snapshot(repo),
        "source_root": str(SOURCE),
    }
    write_json(case / "receipt.json", receipt)
    return receipt

def api_off_case():
    case = EVIDENCE / "existing-api-disabled-control"
    case.mkdir()
    repo, replies, diff = author_project(case, True)
    before = snapshot(repo)
    env = environment(case)
    script = (
        "import json,sys\nfrom pathlib import Path\n"
        "from testpilot.loop import TestPilot\nfrom testpilot.model import ScriptedModel\n"
        "p=TestPilot(ScriptedModel.from_dir(sys.argv[2]),max_repair_rounds=0,"
        "timeout_s=15,coverage=False,python=sys.executable)\n"
        "result=p.run(sys.argv[1],Path(sys.argv[3]).read_bytes().decode('utf-8','surrogateescape'))\n"
        "Path(sys.argv[4]).write_text(json.dumps(result.to_dict(),indent=2)+'\\n',encoding='utf-8')\n"
        "print(json.dumps({'status':result.status,'ok':result.ok,'model_calls':len(p.client.calls)}))\n"
        "raise SystemExit(0 if result.ok else 1)\n"
    )
    (case / "control.py").write_text(script, encoding="utf-8")
    command = [
        sys.executable, "-B", str(case / "control.py"), str(repo), str(replies),
        str(case / "change.diff"), str(case / "report.json"),
    ]
    completed = subprocess.run(command, cwd=case, env=env, capture_output=True, timeout=55)
    (case / "stdout.log").write_bytes(completed.stdout)
    (case / "stderr.log").write_bytes(completed.stderr)
    report_path = case / "report.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else None
    receipt = {
        "label": "existing-api-disabled-control", "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.decode("utf-8", "backslashreplace"),
        "stderr": completed.stderr.decode("utf-8", "backslashreplace"),
        "report": report, "input_before": before, "input_after": snapshot(repo),
        "input_unchanged": before == snapshot(repo),
    }
    write_json(case / "receipt.json", receipt)
    return receipt

def main():
    assert shutil.disk_usage(ROOT).free > 5_000_000
    EVIDENCE.mkdir(exist_ok=False)
    before = snapshot(SOURCE)
    write_json(EVIDENCE / "started.json", {
        "python": sys.version, "executable": sys.executable,
        "pytest": importlib.metadata.version("pytest"), "coverage": importlib.metadata.version("coverage"),
        "source_commit": "f3b2135cad31852b599350564fe76dd160a6a522",
        "platform": platform.platform(), "thinkpad_probe_outcome": "unknown; not replayed",
        "source_before": before, "receiver_sha256": digest(Path(__file__).read_bytes()),
    })
    cases = [
        cli_case("default-broken-coverage-plugin", instrumentation_error=True, disable=False),
        api_off_case(),
        cli_case("missing-cli-option", instrumentation_error=True, disable=True),
        cli_case("default-ordinary-control", instrumentation_error=False, disable=False),
    ]
    after = snapshot(SOURCE)
    summary = {
        "source_unchanged": before == after,
        "all_project_inputs_unchanged": all(c["input_unchanged"] for c in cases),
        "cases": [{
            "label": c["label"], "returncode": c["returncode"],
            "status": c["report"]["status"] if c["report"] else None,
            "final": c["report"].get("final") if c["report"] else None,
            "coverage_delta": c["report"].get("coverage") if c["report"] else None,
            "stderr": c["stderr"],
        } for c in cases],
    }
    write_json(EVIDENCE / "SUMMARY.json", summary)
    print(json.dumps({
        "source_unchanged": summary["source_unchanged"],
        "all_project_inputs_unchanged": summary["all_project_inputs_unchanged"],
        "cases": [{
            "label": c["label"], "returncode": c["returncode"], "status": c["status"],
            "final_returncode": c["final"]["returncode"] if c["final"] else None,
            "passed": c["final"]["passed"] if c["final"] else None,
            "failed": c["final"]["failed"] if c["final"] else None,
            "coverage_available": c["coverage_delta"] is not None,
            "authored_coverage_initialization_error": bool(c["final"] and "authored optional coverage plugin cannot initialize" in c["final"].get("output","")),
            "stderr": c["stderr"][:300],
        } for c in summary["cases"]],
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
