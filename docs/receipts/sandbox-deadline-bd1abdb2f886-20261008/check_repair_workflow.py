"""Run an authored timeout/repair through TestPilot and actual pytest subprocesses."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


if os.name != "posix":
    raise SystemExit("This receiving witness requires POSIX process groups.")
source = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(source))
from testpilot.loop import TestPilot
from testpilot.model import RoutingConfig, ScriptedModel


with tempfile.TemporaryDirectory(prefix="testpilot-deadline-workflow-") as td:
    root = Path(td)
    repo = root / "source"
    repo.mkdir()
    marker = root / "helper.pid"

    def git(*args, input=None):
        return subprocess.run(
            ["git", "-C", str(repo), "-c", "core.autocrlf=false",
             "-c", "core.hooksPath=/dev/null", *args], input=input,
            capture_output=True, text=True, encoding="utf-8", check=True,
        )

    git("init", "-q")
    module = repo / "price.py"
    module.write_text("def price():\n    return 1\n")
    git("add", "--", "price.py")
    git("-c", "user.name=Authored Test", "-c", "user.email=authored@example.invalid",
        "commit", "-qm", "authored baseline")
    module.write_text("def price():\n    return 2\n")
    diff = git("diff", "--").stdout
    existing = repo / "tests/test_existing.py"
    existing.parent.mkdir()
    existing.write_text("from price import price\n\ndef test_existing():\n    assert price() > 0\n")
    before = {p.relative_to(repo).as_posix(): p.read_bytes() for p in [module, existing]}
    bad_test = f"""\
from price import price
import pathlib, subprocess, sys, time

def test_price(capfd):
    with capfd.disabled():
        helper = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(6)'],
                                  start_new_session=True)
        pathlib.Path({str(marker)!r}).write_text(str(helper.pid))
        print('authored-detached-helper-ready', flush=True)
        time.sleep(20)
    assert price() == 2
"""
    repaired = "from price import price\n\ndef test_price():\n    assert price() == 2\n"
    client = ScriptedModel([
        "Check the edited price value and repair any blocking test fixture.",
        f"```python path=tests/test_price.py\n{bad_test}```",
        f"```python path=tests/test_price.py\n{repaired}```",
    ])
    started = time.monotonic()
    try:
        result = TestPilot(
            client, RoutingConfig(planner_model="authored-planner", editor_model="authored-editor"),
            max_repair_rounds=1, timeout_s=1, coverage=False,
        ).run(repo, diff)
        elapsed = time.monotonic() - started
        first = result.rounds[0].result
        assert marker.exists(), "the detached helper must actually start"
        assert result.status == "passed" and result.repair_rounds_used == 1
        assert result.tests_written == 1 and len(client.calls) == 3
        assert first["timed_out"] and first["returncode"] is None
        assert "authored-detached-helper-ready" in first["output"]
        assert result.final["passed"] == 2 and not result.final["timed_out"]
        assert all((repo / name).read_bytes() == data for name, data in before.items())
        assert not (repo / "tests/test_price.py").exists()
        check = git("apply", "--check", "-", input=result.patch)
        receipt = {
            "source_root": str(source),
            "sandbox_sha256": hashlib.sha256((source / "testpilot/sandbox.py").read_bytes()).hexdigest(),
            "configured_pytest_timeout_s": 1,
            "observed_pipeline_duration_s": round(elapsed, 3),
            "first_round": {k: first[k] for k in ["returncode", "timed_out", "duration_s", "output", "summary"]},
            "status": result.status, "repair_rounds_used": result.repair_rounds_used,
            "model_calls": len(client.calls), "tests_written": result.tests_written,
            "final": result.final, "patch": result.patch,
            "git_apply_check_returncode": check.returncode,
            "source_files_unchanged": True, "generated_test_absent_from_source": True,
            "scope": "Authored local ScriptedModel replies and actual pytest; no provider or installed runtime.",
        }
    finally:
        if marker.exists():
            try:
                os.killpg(int(marker.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass
    destination.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: receipt[k] for k in ["status", "repair_rounds_used", "model_calls", "observed_pipeline_duration_s"]}))
