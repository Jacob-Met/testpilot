"""Replay an authored Unicode-module edit through TestPilot and actual pytest."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

source = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(source))
from testpilot.loop import TestPilot
from testpilot.model import RoutingConfig, ScriptedModel

with tempfile.TemporaryDirectory(prefix="testpilot-quoted-workflow-") as td:
    repo = Path(td)
    def git(*args, input=None):
        return subprocess.run(["git", "-C", str(repo), "-c", "core.autocrlf=false",
                               "-c", "core.hooksPath=/dev/null", *args], input=input,
                              capture_output=True, text=True, encoding="utf-8", check=True)
    git("init", "-q")
    module = repo / "café.py"
    module.write_text("def price():\n    return 1\n", encoding="utf-8")
    git("add", "--", "café.py")
    git("-c", "user.name=Authored Test", "-c", "user.email=authored@example.invalid",
        "commit", "-qm", "authored baseline")
    module.write_text("def price():\n    return 2\n", encoding="utf-8")
    diff = git("-c", "core.quotePath=true", "diff", "--").stdout
    client = ScriptedModel([
        "Verify that café.price returns the edited value.",
        "```python path=tests/test_price.py\nfrom café import price\n\ndef test_price():\n    assert price() == 2\n```",
    ])
    result = TestPilot(client, RoutingConfig(planner_model="authored-planner", editor_model="authored-editor"),
                       max_repair_rounds=0, timeout_s=10, coverage=True).run(repo, diff)
    receipt = {
        "source_root": str(source), "status": result.status, "changed_functions": result.changed_functions,
        "tests_written": result.tests_written, "model_calls": len(client.calls),
        "final": result.final, "coverage": result.coverage, "patch": result.patch,
        "fixture_module_unchanged_after_pipeline": module.read_text(encoding="utf-8") == "def price():\n    return 2\n",
        "generated_test_absent_from_source_after_pipeline": not (repo / "tests/test_price.py").exists(),
    }
    if result.patch:
        check = git("apply", "--check", "-", input=result.patch)
        receipt["git_apply_check_returncode"] = check.returncode
    destination.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key:receipt[key] for key in ("status", "tests_written", "model_calls")}, ensure_ascii=False))
