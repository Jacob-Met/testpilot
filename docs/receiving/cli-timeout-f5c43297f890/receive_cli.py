"""Preserve actual run CLI before/after timeout admission observations."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import datetime

source = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()
destination.mkdir(parents=True, exist_ok=False)
fixture = destination / "fixture"
fixture.mkdir()
repo = fixture / "repo"
repo.mkdir()
diff = fixture / "empty.diff"
diff.write_bytes(b"")
script = fixture / "script"
script.mkdir()
(script / "01.txt").write_text("unused authored response", encoding="utf-8")
records = []
env = os.environ.copy()
env["PYTHONPATH"] = str(source)
env["PYTHONDONTWRITEBYTECODE"] = "1"
for index, value in enumerate(("nan", "NaN", "inf", "+inf", "-inf", "1e309", "0", "-0.0", "-1", "0.125", "6e1")):
    case = destination / ("%02d" % index)
    case.mkdir()
    out = case / "out"
    out.mkdir()
    old = {}
    for name in ("report.json", "report.md", "report.html", "testpilot.patch"):
        raw = ("previous completed review: " + name).encode()
        (out / name).write_bytes(raw)
        old[name] = hashlib.sha256(raw).hexdigest()
    cmd = [sys.executable, "-B", "-m", "testpilot", "run", "--repo", str(repo),
           "--diff", str(diff), "--script", str(script), "--out", str(out), "--timeout=" + value]
    result = subprocess.run(cmd, cwd=source, env=env, capture_output=True, timeout=30)
    (case / "stdout.txt").write_bytes(result.stdout)
    (case / "stderr.txt").write_bytes(result.stderr)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()}
    recorded_status = None
    model_entries = None
    try:
        report = json.loads((out / "report.json").read_bytes())
        recorded_status = report["status"]
        model_entries = len(report["ledger"]["entries"])
    except (ValueError, KeyError, TypeError):
        pass
    row = {"timeout": value, "returncode": result.returncode,
           "previous_outputs_preserved": old == after, "before_sha256": old,
           "after_sha256": after, "status": recorded_status, "model_entries": model_entries,
           "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
           "stderr_sha256": hashlib.sha256(result.stderr).hexdigest()}
    records.append(row)
    print(json.dumps({k: row[k] for k in ("timeout", "returncode", "previous_outputs_preserved", "status", "model_entries")}), flush=True)
pin = lambda path: hashlib.sha256((source / path).read_bytes()).hexdigest()
receipt = {"recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "source_main": subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip(),
           "python": sys.version, "source_path": str(source),
           "source_sha256": {x:pin(x) for x in ("testpilot/__main__.py","testpilot/sandbox.py","testpilot/loop.py","testpilot/recheck.py")},
           "cases": records}
(destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print("RECEIPT", hashlib.sha256((destination / "receipt.json").read_bytes()).hexdigest(), flush=True)
