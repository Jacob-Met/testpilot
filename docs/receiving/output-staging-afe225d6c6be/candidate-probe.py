# SPDX-License-Identifier: Apache-2.0
"""Read-only source scout using the real writer and owned OS-limited children."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys

from testpilot.loop import Ledger, LoopResult, make_patch, write_outputs
from testpilot.model import RoutingConfig


def result(root: Path, marker: str, padding: int) -> LoopResult:
    repo = root / "empty-authored-repo"
    repo.mkdir(exist_ok=True)
    source = f"# {marker}\n" + "# padding for an owned write-limit control\n" * padding
    source += "def test_authored_example():\n    assert 2 + 2 == 4\n"
    files = {"tests/test_authored_example.py": source}
    return LoopResult(
        status="no_tests", changed_functions=[], repair_rounds_used=0,
        max_repair_rounds=0, test_files=files, tests_written=1, final=None,
        patch=make_patch(repo, files, additions_only=True), coverage=None,
        ledger=Ledger(RoutingConfig()).to_dict(), rounds=[], plan=f"Plan {marker}",
        message="Authored output-publication fixture; no test execution or model claim.",
    )


def state(folder: Path) -> dict:
    answer = {}
    for name in ["testpilot.patch", "report.json", "report.md", "report.html"]:
        data = (folder / name).read_bytes()
        answer[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return answer


if len(sys.argv) > 1 and sys.argv[1] == "child":
    folder, cap, padding = Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    replacement = result(folder.parent, "NEW_REVIEW", padding)
    if cap:
        signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
        resource.setrlimit(resource.RLIMIT_FSIZE, (cap, cap))
    try:
        write_outputs(replacement, folder)
    except OSError as error:
        print(json.dumps({"status": "OUTPUT_ERROR", "type": type(error).__name__,
                          "errno": error.errno, "error": str(error), "limit": cap,
                          "patchBytesRequested": len(replacement.patch.encode())}))
        raise SystemExit(27)
    print(json.dumps({"status": "WRITTEN", "limit": cap,
                      "patchBytesRequested": len(replacement.patch.encode())}))
    raise SystemExit(0)


root = Path(sys.argv[1])
root.mkdir(parents=True, exist_ok=True)
cases = []
for name, cap, padding in [
    ("ordinary_replacement", 0, 0),
    ("early_patch_write_limit", 4096, 300),
    ("late_html_write_limit", 4096, 0),
]:
    work = root / name
    work.mkdir()
    folder = work / "saved-review"
    original = result(work, "OLD_KEPT_REVIEW", 0)
    write_outputs(original, folder)
    before = state(folder)
    run = subprocess.run(
        [sys.executable, "-B", __file__, "child", str(folder), str(cap), str(padding)],
        capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        timeout=20,
    )
    after = state(folder)
    changed = [key for key in before if before[key] != after[key]]
    observation = {"id": name, "returncode": run.returncode, "stdout": run.stdout,
                   "stderr": run.stderr, "before": before, "after": after,
                   "changedSavedArtifacts": changed}
    if cap == 0:
        assert run.returncode == 0, observation
        assert len(changed) == 4, observation
        assert b"NEW_REVIEW" in (folder / "testpilot.patch").read_bytes()
        observation["interpretation"] = "Ordinary native replacement succeeds and publishes the new authored review."
    else:
        assert run.returncode == 27, observation
        child = json.loads(run.stdout)
        assert child["errno"] == 27, observation
        assert changed == [], observation
        assert set(p.name for p in folder.iterdir()) == set(before), observation
        observation["interpretation"] = "The actual staged writer failed and preserved all four previously saved artifacts."
    cases.append(observation)

receipt = {
    "status": "PRESERVED_TWO_REAL_OS_FAILURES_AND_PUBLISHED_CHANGED_REVIEW",
    "repository": "Jacob-Met/testpilot",
    "base": "e2285d68b2ea5eb2158c0a7e0d936ce5d56f8ff5",
    "tree": "22da6a890c2befaf72d3826103538491b07793df",
    "phase": "candidate",
    "baselineWriterBlob": "3057a9c7c9777a23e73f8b56979670001eb512fd",
    "writerBlob": "ed0f5f7f057c217b931a1756bd679ae087247e0a",
    "python": sys.version,
    "method": "Unmodified write_outputs with real LoopResult/make_patch; RLIMIT_FSIZE applies only inside a new owned child; no mocked writer, model, network or production file.",
    "scopeLimit": "This proves preparation/staging failure preservation and a changed-input normal write. It does not establish crash atomicity, concurrent-writer safety or whole-set rollback after replacement begins.",
    "cases": cases,
}
print(json.dumps(receipt, indent=2))
