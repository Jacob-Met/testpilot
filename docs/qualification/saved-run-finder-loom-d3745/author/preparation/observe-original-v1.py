import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "original"
OUT = ROOT / "original-observation-v1"

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def snapshot():
    rows = []
    for p in sorted(SOURCE.rglob("*")):
        s = p.lstat()
        row = {"path": p.relative_to(SOURCE).as_posix(), "mode": oct(stat.S_IMODE(s.st_mode)), "type": "directory" if stat.S_ISDIR(s.st_mode) else "file"}
        if stat.S_ISREG(s.st_mode):
            raw = p.read_bytes()
            row.update(bytes=len(raw), sha256=digest(raw))
        else:
            assert stat.S_ISDIR(s.st_mode)
        rows.append(row)
    return rows

OUT.mkdir()
intake = json.loads((ROOT / "preparation/source-intake-v1.json").read_bytes())
for row in intake["files"]:
    p = SOURCE / row["path"]
    raw = p.read_bytes()
    assert len(raw) == row["bytes"] and digest(raw) == row["sha256"]
    assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == row["git_blob"]
before = snapshot()
argv = [sys.executable, "-B", "-m", "testpilot", "history", "--root", str(SOURCE / "eval/results")]
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
child = subprocess.run(argv, cwd=SOURCE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
(OUT / "stdout.bin").write_bytes(child.stdout)
(OUT / "stderr.bin").write_bytes(child.stderr)
after = snapshot()
checks = [
    {"name": "original missing history command", "actual": child.returncode, "expected": 2},
    {"name": "original stdout empty", "actual": child.stdout, "expected": b""},
    {"name": "argparse explicitly refuses history", "actual": b"invalid choice: 'history'" in child.stderr, "expected": True},
    {"name": "all original files and namespaces unchanged", "actual": after, "expected": before},
]
rows = [{"name": c["name"], "passed": c["actual"] == c["expected"]} for c in checks]
receipt = {
    "schema": "hamon.loom.testpilot-history.original-command-observation.v1",
    "started": started,
    "finished": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "accepted_original_witness": all(c["passed"] for c in rows),
    "candidate_exists": False,
    "source_commit": intake["commit"],
    "source_tree": intake["tree"],
    "python": {"executable": sys.executable, "version": sys.version, "platform": platform.platform()},
    "argv": argv,
    "cwd": str(SOURCE),
    "exit_code": child.returncode,
    "stdout": {"path": "stdout.bin", "bytes": len(child.stdout), "sha256": digest(child.stdout)},
    "stderr": {"path": "stderr.bin", "bytes": len(child.stderr), "sha256": digest(child.stderr), "text": child.stderr.decode("utf-8")},
    "checks": rows,
    "before": before,
    "after": after,
    "scope": "One actual unchanged CLI admission refusal. No tests, generation, model, report execution or historical Mac course was run. Original producer-retained calc_clamp/stats_median reports were not changed.",
}
data = (json.dumps(receipt, indent=2, ensure_ascii=True) + "\n").encode()
(OUT / "receipt.json").write_bytes(data)
print(json.dumps({"accepted_original_witness": receipt["accepted_original_witness"], "commands": 1, "checks": len(rows), "exit_code": child.returncode, "receipt_bytes": len(data), "receipt_sha256": digest(data)}))
raise SystemExit(0 if receipt["accepted_original_witness"] else 1)
