"""Run the unchanged CLI receiver and attach explicit current-parent provenance."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path("/Users/me/testpilot-cancellation-18a24bf0c281")
source = ROOT / "candidate"
driver = ROOT / "receiving/receive_cancellation.py"
expected = "e80ecd44e02f6bc32c0994bc1665c8ed21c86fa6de266f81a2a0043d0d72b16c"
if hashlib.sha256(driver.read_bytes()).hexdigest() != expected:
    raise ValueError("The originally frozen receiver changed")
freeze = json.loads((ROOT / "evidence/candidate-source-freeze.json").read_text())
for row in freeze["files"]:
    if hashlib.sha256((source / row["path"]).read_bytes()).hexdigest() != row["sha256"]:
        raise ValueError(f"Frozen candidate source changed: {row['path']}")
output = ROOT / "evidence/candidate-cli"
argv = [sys.executable, str(driver), "--source", str(source), "--output", str(output)]
started = time.monotonic()
with (ROOT / "evidence/candidate-cli.stdout").open("wb") as stdout, (ROOT / "evidence/candidate-cli.stderr").open("wb") as stderr:
    result = subprocess.run(argv, cwd=ROOT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                            stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, timeout=45)
raw = json.loads((output / "receipt.json").read_text())
for row in freeze["files"]:
    if hashlib.sha256((source / row["path"]).read_bytes()).hexdigest() != row["sha256"]:
        raise ValueError(f"Frozen candidate source changed during receiving: {row['path']}")
receipt = {
    "source_commit": "649dc7d1fd02493af298876eea0697849404bba9",
    "actual_canonical_parent": "7f44c4f134f4d56d37dd14c7c2d2aaa3c8c8749e",
    "actual_canonical_tree": "ea3f7b4170f1515abb7188d31dc269623b9e0738",
    "actual_source": str(source), "source_freeze": freeze["files"],
    "raw_receiver_receipt": str(output / "receipt.json"),
    "raw_receiver_receipt_sha256": hashlib.sha256((output / "receipt.json").read_bytes()).hexdigest(),
    "historical_label_notice": "The unchanged frozen receiver contains hardcoded canonical_head/source_tree fields naming its original f3 discovery source. They are historical labels, not the executed source identity for this candidate run. The actual executed current parent plus repair and all input hashes are explicitly bound here; raw receipt bytes are preserved.",
    "argv": argv, "exit_code": result.returncode, "elapsed_s": time.monotonic() - started,
    "platform": platform.platform(), "python": sys.version,
    "driver_sha256": expected, "checks": raw["checks"],
    "source_unchanged": raw["source_before"] == raw["source_after"],
    "scope": "Two actual native CLI actions with the unchanged frozen receiver; no live provider or developer repository. Original f3 evidence remains separate. This receipt qualifies the exact current7f44 staging composition plus the cancellation repair."
}
(ROOT / "evidence/candidate-cli-composition.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"exit_code": result.returncode, "checks": raw["checks"],
                  "passed": sum(raw["checks"].values()), "total": len(raw["checks"]),
                  "source_unchanged": receipt["source_unchanged"],
                  "canonical_parent": receipt["actual_canonical_parent"]}))
raise SystemExit(result.returncode)
