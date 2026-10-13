"""Focused original-first saved-comparison author course; never runs report-listed tests."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

def identity(path):
    data = path.read_bytes()
    s = path.stat()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(),
            "mode": stat.S_IMODE(s.st_mode), "mtime_ns": s.st_mtime_ns, "inode": s.st_ino}

def inventory(root):
    return {p.relative_to(root).as_posix(): identity(p)
            for p in sorted(root.rglob("*")) if p.is_file()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("original", "candidate"), required=True)
    parser.add_argument("--packet", type=Path, required=True)
    args = parser.parse_args()
    if sys.version_info < (3, 12):
        raise RuntimeError("TestPilot declares Python >=3.12")
    root = Path("/home/jacob/hamon-dcac8b3b8755-testpilot-diagnostics-author-v1")
    root.mkdir(exist_ok=True)
    out = root / args.mode
    out.mkdir()
    source = out / "source"
    source.mkdir()
    temp = out / "tmp"
    temp.mkdir()
    packet_before = identity(args.packet)
    payload = json.loads(args.packet.read_text(encoding="utf-8"))
    names = set()
    for item in payload["files"]:
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts or item["path"] in names:
            raise ValueError("Invalid or duplicate source path")
        names.add(item["path"])
        data = item["content"].encode("utf-8")
        if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError("Source bytes do not match packet")
        digest = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if digest != item["git_blob"] or item["mode"] != "100644":
            raise ValueError("Source Git tuple does not match packet")
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(data)
        target.chmod(0o644)
    before = inventory(source)
    selected = ["tests/test_compare_diagnostics.py"]
    if args.mode == "candidate":
        selected += [
            "tests/test_compare.py::test_exact_download_bytes_and_detached_immutable_data",
            "tests/test_compare.py::test_unknown_junit_does_not_promote_authored_counts_or_incomplete_cost",
            "tests/test_compare.py::test_context_never_pairs_duplicate_labels_or_treats_a_rename_as_identity",
            "tests/test_compare.py::test_lexical_decimal_amounts_are_preserved_without_float_underflow",
        ]
    command = [sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-q",
               "--basetemp", str(temp / "pytest"), "--junitxml", str(out / "junit.xml"), *selected]
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
                       TMPDIR=str(temp), TEMP=str(temp), TMP=str(temp))
    start = time.time()
    child = subprocess.Popen(command, cwd=source, env=environment,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timeout = False
    try:
        stdout, stderr = child.communicate(timeout=45)
    except subprocess.TimeoutExpired:
        timeout = True
        child.kill()
        stdout, stderr = child.communicate()
    (out / "pytest.stdout.txt").write_bytes(stdout)
    (out / "pytest.stderr.txt").write_bytes(stderr)
    suite = ET.parse(out / "junit.xml").getroot()
    cases = suite.findall(".//testcase")
    counts = {"selected": len(cases), "failed": sum(c.find("failure") is not None for c in cases),
              "error": sum(c.find("error") is not None for c in cases),
              "skipped": sum(c.find("skipped") is not None for c in cases)}
    counts["passed"] = counts["selected"] - counts["failed"] - counts["error"] - counts["skipped"]
    expected = ({"selected": 5, "failed": 3, "error": 0, "skipped": 0, "passed": 2}
                if args.mode == "original" else
                {"selected": 9, "failed": 0, "error": 0, "skipped": 0, "passed": 9})
    after = inventory(source)
    packet_after = identity(args.packet)
    passed = (counts == expected and child.returncode == (1 if args.mode == "original" else 0)
              and not timeout and before == after and packet_before == packet_after)
    receipt = {
        "schema": "hamon.testpilot-diagnostics-author/1", "mode": args.mode,
        "scope": "Maintained saved-report renderer tests only; no report-listed test/provider execution",
        "python": platform.python_version(), "platform": platform.platform(),
        "pid": os.getpid(), "child_pid": child.pid, "command": command,
        "returncode": child.returncode, "timed_out": timeout,
        "duration_s": time.time() - start, "counts": counts, "expected": expected,
        "source_before": before, "source_after": after, "source_preserved": before == after,
        "packet_before": packet_before, "packet_after": packet_after,
        "packet_preserved": packet_before == packet_after,
        "streams": {name: identity(out / name) for name in ("pytest.stdout.txt", "pytest.stderr.txt", "junit.xml")},
        "passed": passed,
    }
    (out / "receiving.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mode": args.mode, "passed": passed, "child_pid": child.pid,
                      "returncode": child.returncode, "counts": counts,
                      "source_preserved": before == after, "receipt": str(out / "receiving.json")}))
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
