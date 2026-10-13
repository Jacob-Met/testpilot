"""Receive the real history CLI against independently prepared literal oracles.

This controller imports no TestPilot code. It executes only the explicit history
commands in the frozen case specification, in separate owned Python processes.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time
import traceback

SPEC_SHA = "6793d9d1466011524f7541c321231f3be78a20addd3170cca257bfd93c07cdbf"
CASE_COUNT = 34
TIMEOUT_SECONDS = 25


def encoded(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write_new(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)


def metadata(path, cache=None):
    """lstat links/FIFOs; open only observed regular files in owned inputs."""
    s = path.lstat()
    value = {"path": str(path), "mode": stat.S_IMODE(s.st_mode),
             "mtime_ns": s.st_mtime_ns, "inode": s.st_ino,
             "device": s.st_dev, "links": s.st_nlink}
    if stat.S_ISLNK(s.st_mode):
        value.update(kind="symlink", target=os.readlink(path))
    elif stat.S_ISDIR(s.st_mode):
        value.update(kind="directory")
    elif stat.S_ISFIFO(s.st_mode):
        value.update(kind="fifo")
    elif stat.S_ISREG(s.st_mode):
        key = (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if cache is None or key not in cache:
            h = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(block)
            actual_hash = h.hexdigest()
            if cache is not None:
                cache[key] = actual_hash
        else:
            actual_hash = cache[key]
        value.update(kind="regular", bytes=s.st_size, sha256=actual_hash)
    else:
        raise ValueError("Unexpected owned input type: " + str(path))
    return value


def namespace(roots):
    rows = {}
    cache = {}
    def visit(path):
        value = metadata(path, cache)
        rows[str(path)] = value
        if value["kind"] == "directory":
            for child in sorted(path.iterdir(), key=lambda p: p.name):
                visit(child)
    for root in roots:
        visit(root)
    return rows


def pins_match(actual, pin):
    return all(actual.get(k) == pin[k] for k in
               ("kind", "bytes", "sha256", "mode", "target") if k in pin)


def compare(before, after):
    changes = [{"path": p, "before": before.get(p), "after": after.get(p)}
               for p in sorted(set(before) | set(after))
               if before.get(p) != after.get(p)]
    return {"unchanged": not changes, "before_records": len(before),
            "after_records": len(after), "before_sha256": digest(encoded(before)),
            "after_sha256": digest(encoded(after)), "changes": changes}


def group_exists(pid):
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return False
    return True


def run_case(case, root, output, environment):
    folder = output / case["name"]
    folder.mkdir()
    command = [sys.executable, "-S", "-B", "-m", "testpilot", *case["args"]]
    row = {"name": case["name"], "command": command, "cwd": str(root),
           "started": now(), "timeout_seconds": TIMEOUT_SECONDS,
           "timed_out": False, "owned_group_cleanup": []}
    started = time.monotonic()
    process = None
    with (folder / "stdout.bin").open("xb") as stdout, (folder / "stderr.bin").open("xb") as stderr:
        try:
            process = subprocess.Popen(command, cwd=root, env=environment,
                                       stdin=subprocess.DEVNULL, stdout=stdout,
                                       stderr=stderr, start_new_session=True)
            row["pid"] = process.pid
            try:
                row["returncode"] = process.wait(timeout=TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                row["timed_out"] = True
        finally:
            if process is not None:
                alive = group_exists(process.pid)
                row["owned_group_absent_before_cleanup"] = not alive
                if alive:
                    os.killpg(process.pid, signal.SIGTERM)
                    row["owned_group_cleanup"].append("SIGTERM")
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass
                    if group_exists(process.pid):
                        os.killpg(process.pid, signal.SIGKILL)
                        row["owned_group_cleanup"].append("SIGKILL")
                process.wait(timeout=2)
                row["returncode"] = process.returncode
                row["owned_group_absent_after_cleanup"] = not group_exists(process.pid)
    row["duration_seconds"] = time.monotonic() - started
    row["finished"] = now()
    actual_out = (folder / "stdout.bin").read_bytes()
    actual_err = (folder / "stderr.bin").read_bytes()
    expected_out = Path(case["expected_stdout_path"]).read_bytes()
    expected_err = case["expected_stderr"]
    stderr_ok = (actual_err == expected_err.encode() if expected_err is not None
                 else case["stderr_contains"].encode() in actual_err)
    row["stdout"] = {"bytes": len(actual_out), "sha256": digest(actual_out)}
    row["stderr"] = {"bytes": len(actual_err), "sha256": digest(actual_err)}
    row["expected"] = {k: v for k, v in case.items() if k.startswith("expected_") or k == "stderr_contains"}
    row["checks"] = {"exit": row["returncode"] == case["expected_exit"],
                     "exact_stdout": actual_out == expected_out, "stderr": stderr_ok,
                     "no_timeout": not row["timed_out"],
                     "normal_process_closure": row["owned_group_absent_before_cleanup"] and row["owned_group_absent_after_cleanup"]}
    row["accepted"] = all(row["checks"].values())
    write_new(folder / "result.json", encoded(row))
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", required=True, type=Path)
    parser.add_argument("--candidate-root", required=True, type=Path)
    parser.add_argument("--candidate-pins", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.candidate_root.resolve(strict=True)
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"schema": "hamon.root.testpilot-history.independent-receipt.v1",
               "started": now(), "accepted": False, "cases": [],
               "python": sys.version, "executable": sys.executable,
               "scope": "Actual CLI history commands only; exact public-contract stdout bytes, fixed true limits, owned input/source/control preservation. No global network/process audit, hostile filesystem race, installed consumer, or renewed historical execution claim."}
    controls_before = inputs_before = source_before = None
    try:
        freeze = json.loads(args.freeze.read_bytes())
        controls = freeze["controls"]
        if not any(Path(p["path"]).resolve() == Path(__file__).resolve() for p in controls):
            raise ValueError("This receiver is absent from the frozen controls")
        controls_before = {p["path"]: metadata(Path(p["path"])) for p in controls}
        if not all(pins_match(controls_before[p["path"]], p) for p in controls):
            raise ValueError("Frozen control mismatch")
        controls_before[str(args.freeze.absolute())] = metadata(args.freeze.absolute())
        spec_path = Path(freeze["case_spec_path"])
        raw_spec = spec_path.read_bytes()
        if digest(raw_spec) != SPEC_SHA:
            raise ValueError("Case specification is not the independently prepared body")
        spec = json.loads(raw_spec)
        cases = spec["cases"]
        if len(cases) != CASE_COUNT or len({c["name"] for c in cases}) != CASE_COUNT:
            raise ValueError("Case membership mismatch")
        for c in cases:
            if not re.fullmatch(r"[a-zA-Z0-9-]+", c["name"]) or c["args"][0] != "history":
                raise ValueError("Non-history or unsafe case")
            raw = Path(c["expected_stdout_path"]).read_bytes()
            if len(raw) != c["expected_stdout_bytes"] or digest(raw) != c["expected_stdout_sha256"]:
                raise ValueError("Expected stdout identity mismatch")
        input_roots = [spec_path.parent / "inputs", spec_path.parent / "seeds"]
        inputs_before = namespace(input_roots)
        expected_leaves = {p["path"]: p for p in spec["files"]}
        actual_leaves = {p: v for p, v in inputs_before.items() if v["kind"] != "directory"}
        if set(actual_leaves) != set(expected_leaves):
            raise ValueError("Input leaf namespace mismatch")
        for path, pin in expected_leaves.items():
            if not pins_match(actual_leaves[path], pin):
                raise ValueError("Input identity mismatch: " + path)
            if "hardlink_to" in pin:
                other = actual_leaves[pin["hardlink_to"]]
                if (other["device"], other["inode"]) != (actual_leaves[path]["device"], actual_leaves[path]["inode"]):
                    raise ValueError("Declared hardlink identity mismatch")
        expected_dirs = {p for p in spec["directories"] if any(Path(p) == r or r in Path(p).parents for r in input_roots)}
        if {p for p, v in inputs_before.items() if v["kind"] == "directory"} != expected_dirs:
            raise ValueError("Input directory namespace mismatch")
        candidate_pins = json.loads(args.candidate_pins.read_bytes())
        if Path(candidate_pins["root"]).resolve() != root:
            raise ValueError("Candidate manifest root mismatch")
        source_before = namespace([root])
        expected_source = {}
        for pin in candidate_pins["files"]:
            rel = Path(pin["path"])
            if rel.is_absolute() or ".." in rel.parts:
                raise ValueError("Unsafe candidate pin path")
            expected_source[str(root / rel)] = pin
        actual_source = {p: v for p, v in source_before.items() if v["kind"] != "directory"}
        if set(actual_source) != set(expected_source) or not all(
                actual_source[p]["kind"] == "regular" and pins_match(actual_source[p], pin)
                for p, pin in expected_source.items()):
            raise ValueError("Candidate complete source manifest mismatch")
        controls_before[str(args.candidate_pins.absolute())] = metadata(args.candidate_pins.absolute())
        environment = {"PATH": "", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0",
                       "PYTHONIOENCODING": "utf-8", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
        receipt["environment"] = environment
        receipt["admission"] = {"accepted": True, "input_files": len(expected_leaves),
                                "input_directories": len(expected_dirs), "source_files": len(expected_source),
                                "case_count": len(cases), "spec_sha256": digest(raw_spec)}
        for case in cases:
            row = run_case(case, root, output, environment)
            receipt["cases"].append(row)
            print(json.dumps({"case": row["name"], "accepted": row["accepted"], "exit": row["returncode"]}), flush=True)
        receipt["accepted"] = all(r["accepted"] for r in receipt["cases"])
    except BaseException as exc:
        receipt["error"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        receipt["accepted"] = False
    finally:
        for label, before, after_fn in [
            ("inputs", inputs_before, lambda: namespace(input_roots)),
            ("source", source_before, lambda: namespace([root])),
            ("controls", controls_before, lambda: {p: metadata(Path(p)) for p in controls_before}),
        ]:
            if before is not None:
                try:
                    receipt[label + "_preservation"] = compare(before, after_fn())
                    receipt["accepted"] = receipt["accepted"] and receipt[label + "_preservation"]["unchanged"]
                except BaseException as exc:
                    receipt[label + "_preservation"] = {"unchanged": False, "error": repr(exc)}
                    receipt["accepted"] = False
        receipt["finished"] = now()
        receipt["cases_passed"] = sum(r["accepted"] for r in receipt["cases"])
        write_new(output / "receipt.json", encoded(receipt))
    print(json.dumps({"accepted": receipt["accepted"], "cases_passed": receipt["cases_passed"], "receipt": str(output / "receipt.json")}), flush=True)
    return 0 if receipt["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
