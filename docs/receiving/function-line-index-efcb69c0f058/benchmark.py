"""Compare complete native targets CLI output on fixed fictional Python diffs.

Run with an interpreter that can run TestPilot's existing CLI. No model or
generated pytest child is invoked. This script does not alter either source root.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=7)
    args = parser.parse_args()
    roots = {"before": args.before.resolve(), "after": args.after.resolve()}
    source_hashes = {name: digest((root / "testpilot/diff.py").read_bytes())
                     for name, root in roots.items()}
    report = {"python": sys.version, "platform": platform.platform(),
              "source_sha256": source_hashes, "samples_per_variant": args.samples,
              "clock": "perf_counter: complete child process, captured output",
              "fixtures": [], "no_model_calls": True}
    with tempfile.TemporaryDirectory(prefix="testpilot-line-index-") as raw:
        work = Path(raw)
        for label, count, stride in [("small-new", 5, 1),
                                     ("dense-new", 2000, 1),
                                     ("sparse-edit", 2000, 100)]:
            fixture = work / label
            fixture.mkdir()
            selected = set(range(0, count, stride))
            source = "".join(f"def f_{i}():\n    return {i}\n\n" for i in range(count))
            (fixture / "many.py").write_text(source, encoding="utf-8")
            if label.endswith("new"):
                lines = source.splitlines()
                change = ("--- /dev/null\n+++ b/many.py\n"
                          f"@@ -0,0 +1,{len(lines)} @@\n"
                          + "".join("+" + line + "\n" for line in lines))
                expected = [{
                    "path": "many.py", "module": "many", "qualname": f"f_{i}",
                    "lineno": 3 * i + 1, "end_lineno": 3 * i + 2,
                    "changed_lines": [3 * i + 1, 3 * i + 2],
                    "source": f"def f_{i}():\n    return {i}", "is_method": False,
                } for i in range(count)]
            else:
                old = "".join(f"def f_{i}():\n    return {i + 1 if i in selected else i}\n\n"
                              for i in range(count))
                change = "".join(difflib.unified_diff(
                    old.splitlines(keepends=True), source.splitlines(keepends=True),
                    fromfile="a/many.py", tofile="b/many.py", n=0))
                expected = [{
                    "path": "many.py", "module": "many", "qualname": f"f_{i}",
                    "lineno": 3 * i + 1, "end_lineno": 3 * i + 2,
                    "changed_lines": [3 * i + 2],
                    "source": f"def f_{i}():\n    return {i}", "is_method": False,
                } for i in sorted(selected)]
            diff = fixture / "change.diff"
            diff.write_text(change, encoding="utf-8")
            inputs = {p.name: digest(p.read_bytes()) for p in [fixture / "many.py", diff]}
            record = {"name": label, "functions": count, "physical_lines": 3 * count,
                      "selected_functions": len(expected), "input_sha256": inputs,
                      "runs": {"before": [], "after": []}}
            first_stdout = None
            for trial in range(args.samples):
                for name in (["before", "after"] if trial % 2 == 0 else ["after", "before"]):
                    command = [sys.executable, "-B", "-m", "testpilot", "targets",
                               "--repo", str(fixture), "--diff", str(diff), "--json"]
                    start = time.perf_counter()
                    child = subprocess.run(command, cwd=roots[name], capture_output=True)
                    elapsed = time.perf_counter() - start
                    if child.returncode != 0 or child.stderr:
                        raise RuntimeError(f"{name}/{label} failed: {child.stderr!r}")
                    if json.loads(child.stdout) != {"changed_functions": expected}:
                        raise RuntimeError(f"{name}/{label} differs from literal fixture expectation")
                    if first_stdout is None:
                        first_stdout = child.stdout
                    elif child.stdout != first_stdout:
                        raise RuntimeError(f"{name}/{label} output bytes differ")
                    record["runs"][name].append({"seconds": elapsed,
                                                  "stdout_bytes": len(child.stdout),
                                                  "stdout_sha256": digest(child.stdout),
                                                  "stderr_bytes": len(child.stderr),
                                                  "exit_code": child.returncode})
            record["median_seconds"] = {name: statistics.median(x["seconds"] for x in samples)
                                         for name, samples in record["runs"].items()}
            record["complete_output_equal"] = True
            record["inputs_unchanged"] = inputs == {
                p.name: digest(p.read_bytes()) for p in [fixture / "many.py", diff]}
            if not record["inputs_unchanged"]:
                raise RuntimeError("fixture input changed")
            report["fixtures"].append(record)
    report["source_unchanged"] = source_hashes == {
        name: digest((root / "testpilot/diff.py").read_bytes()) for name, root in roots.items()}
    if not report["source_unchanged"]:
        raise RuntimeError("selector source changed during benchmark")
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"fixtures": [{"name": x["name"], "median_seconds": x["median_seconds"]}
                                   for x in report["fixtures"]], "source_unchanged": True}, indent=2))


if __name__ == "__main__":
    main()
