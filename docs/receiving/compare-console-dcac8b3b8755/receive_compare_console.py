"""Receive the compare command through actual local pipes and retained files."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    args.out.mkdir()
    temp = args.out / "tmp"
    temp.mkdir()
    document = {
        "status": "no_changes", "changed_functions": [], "test_files": {},
        "tests_written": 0, "repair_rounds_used": 0, "max_repair_rounds": 1,
        "final": None, "coverage": None,
        "ledger": {"total_tokens": 0, "total_cost_usd": 0,
                   "cost_is_complete": False, "tokens_estimated": False,
                   "by_model": {}, "entries": []},
        "rounds": [], "plan": "Fictional retained comparison \u03a9.",
        "message": "", "patch": "",
    }
    before = args.out / "before.json"
    after = args.out / "after.json"
    raw = (json.dumps(document, ensure_ascii=True, indent=2) + "\n").encode()
    before.write_bytes(raw)
    document["message"] = "A separate saved observation."
    after_raw = (json.dumps(document, ensure_ascii=True, indent=2) + "\n").encode()
    after.write_bytes(after_raw)
    invalid = args.out / "invalid.json"
    invalid.write_bytes(b"\xff")
    source_paths = sorted(p for p in source.rglob("*") if p.is_file())
    before_sources = {str(p.relative_to(source)): sha(p.read_bytes()) for p in source_paths}
    records = []
    expected_page = None
    specs = [
        ("open_utf8", "utf-8", False, False, "report.html", "valid", 0, True),
        ("open_ascii", "ascii:strict", False, False, "ascii.html", "valid", 0, True),
        ("stdout_closed", "utf-8", True, False, "pipe.html", "valid", 2, True),
        ("ascii_unicode_path", "ascii:strict", False, False, "caf\u00e9.html", "valid", 2, True),
        ("both_closed", "utf-8", True, True, "both.html", "valid", 2, True),
        ("occupied_destination", "utf-8", False, False, "existing.html", "existing", 2, False),
        ("invalid_closed_stderr", "utf-8", False, True, "invalid.html", "invalid", 2, False),
        ("invalid_unicode_diagnostic", "ascii:strict", False, False, "missing.html", "missing", 2, False),
    ]
    for optimized in (False, True):
        mode = "optimized" if optimized else "normal"
        mode_dir = args.out / mode
        mode_dir.mkdir()
        for name, encoding, close_stdout, close_stderr, filename, input_kind, expected_exit, saves in specs:
            target = mode_dir / filename
            if input_kind == "existing":
                target.write_bytes(b"existing output must survive\n")
            before_arg = invalid if input_kind == "invalid" else (
                args.out / "absent \u03a9.json" if input_kind == "missing" else before)
            command = [sys.executable, "-B"] + (["-O"] if optimized else []) + [
                "-m", "testpilot", "compare", "--before", str(before_arg),
                "--after", str(after), "--out", str(target)]
            env = dict(os.environ)
            env.update(PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE="1",
                       PYTHONIOENCODING=encoding, TMPDIR=str(temp))
            owned = []
            def transport(closed):
                if not closed:
                    return subprocess.PIPE
                read_fd, write_fd = os.pipe()
                os.close(read_fd)
                owned.append(write_fd)
                return write_fd
            try:
                child = subprocess.Popen(command, cwd=source, env=env,
                                         stdout=transport(close_stdout),
                                         stderr=transport(close_stderr))
                for fd in owned:
                    os.close(fd)
                owned.clear()
                stdout, stderr = child.communicate(timeout=20)
            finally:
                for fd in owned:
                    os.close(fd)
            stdout, stderr = stdout or b"", stderr or b""
            prefix = mode_dir / name
            prefix.with_suffix(".stdout").write_bytes(stdout)
            prefix.with_suffix(".stderr").write_bytes(stderr)
            saved = target.read_bytes() if target.is_file() else None
            if name == "open_utf8" and not optimized:
                expected_page = saved
            checks = {
                "expected_exit": child.returncode == expected_exit,
                "input_bytes_preserved": before.read_bytes() == raw and after.read_bytes() == after_raw,
                "no_traceback": b"Traceback" not in stderr and b"Exception ignored" not in stderr,
            }
            if saves:
                checks["complete_html_unchanged"] = saved == expected_page
                if expected_exit == 0:
                    checks["success_stdout_exact"] = stdout == ("wrote " + str(target) + "\n").encode("utf-8")
                    checks["success_stderr_empty"] = stderr == b""
                elif not close_stderr:
                    checks["delivery_diagnostic_exact"] = stderr == b"testpilot: comparison was written, but console delivery failed\n"
            elif input_kind == "existing":
                checks["occupied_bytes_preserved"] = saved == b"existing output must survive\n"
                checks["normal_input_error_diagnostic"] = stderr.startswith(b"testpilot: cannot compare saved reports:")
            else:
                checks["no_output_created"] = saved is None
                checks["stdout_empty"] = stdout == b""
                if input_kind == "missing":
                    checks["normal_input_error_diagnostic"] = stderr.startswith(b"testpilot: cannot compare saved reports:")
            records.append({
                "name": name, "mode": mode, "command": command,
                "encoding": encoding, "stdout_transport": "closed_pipe" if close_stdout else "capture",
                "stderr_transport": "closed_pipe" if close_stderr else "capture",
                "returncode": child.returncode, "expected_returncode": expected_exit,
                "saved_bytes": len(saved) if saved is not None else None,
                "saved_sha256": sha(saved) if saved is not None else None,
                "stdout_sha256": sha(stdout), "stderr_sha256": sha(stderr),
                "stdout_text": stdout.decode("utf-8", "backslashreplace"),
                "stderr_text": stderr.decode("utf-8", "backslashreplace"),
                "checks": checks, "ok": all(checks.values()),
            })
    after_sources = {str(p.relative_to(source)): sha(p.read_bytes()) for p in source_paths}
    receipt = {
        "source": str(source), "python": sys.version, "platform": platform.platform(),
        "source_before": before_sources, "source_after": after_sources,
        "source_unchanged": before_sources == after_sources,
        "normal_and_actual_optimized": True,
        "expected_page_bytes": len(expected_page or b""),
        "expected_page_sha256": sha(expected_page or b""),
        "records": records,
        "passed_cases": sum(r["ok"] for r in records),
        "total_cases": len(records),
        "ok": before_sources == after_sources and all(r["ok"] for r in records),
        "scope": "Fictional saved reports and actual local compare CLI processes; no model, pytest child, project checkout, or provider invocation.",
    }
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=True) + "\n")
    print(json.dumps({k: receipt[k] for k in ("source_unchanged", "expected_page_bytes", "expected_page_sha256", "passed_cases", "total_cases", "ok")}))
    print(json.dumps([{"case": r["name"], "mode": r["mode"], "returncode": r["returncode"], "failed_checks": [k for k,v in r["checks"].items() if not v]} for r in records]))
if __name__ == "__main__":
    main()
