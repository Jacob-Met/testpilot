import json
import os
import subprocess
import sys
from pathlib import Path

from testpilot.__main__ import main

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "LIMIT = 50\n\n\ndef accepts(amount):\n    return amount <= LIMIT\n"
DIFF = "--- a/settings.py\n+++ b/settings.py\n@@ -1 +1 @@\n-LIMIT = 100\n+LIMIT = 50\n"


def test_real_preview_default_and_explicit_stdin(tmp_path):
    (tmp_path / "settings.py").write_text(SOURCE)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    command = [sys.executable, "-B", "-m", "testpilot", "targets",
               "--repo", str(tmp_path), "--diff", "-", "--json"]
    automatic = subprocess.run(command, input=DIFF, cwd=ROOT, env=env,
                               text=True, capture_output=True, check=True)
    assert json.loads(automatic.stdout) == {"changed_functions": []}
    explicit = subprocess.run(command + ["--target", "settings.py::accepts"],
                              input=DIFF, cwd=ROOT, env=env, text=True,
                              capture_output=True, check=True)
    payload = json.loads(explicit.stdout)
    assert payload["selection"]["diff_text"] == DIFF
    assert payload["changed_functions"][0]["source"] == "def accepts(amount):\n    return amount <= LIMIT"
    assert list(tmp_path.iterdir()) == [tmp_path / "settings.py"]


def test_run_refuses_target_before_constructing_model(tmp_path, monkeypatch, capsys):
    diff = tmp_path / "change.diff"
    diff.write_text(DIFF)
    def fail_client(*args, **kwargs):
        raise AssertionError("invalid target constructed a model client")
    monkeypatch.setattr("testpilot.__main__.make_client", fail_client)
    output = tmp_path / "out"
    assert main(["run", "--repo", str(tmp_path), "--diff", str(diff),
                 "--target", "settings.py::missing", "--out", str(output)]) == 2
    assert "invalid target selection" in capsys.readouterr().err
    assert not output.exists()
