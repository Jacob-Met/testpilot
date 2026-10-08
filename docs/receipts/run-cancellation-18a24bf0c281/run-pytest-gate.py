"""Run a finite native pytest gate and bind its complete source/log bytes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import pytest

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("tests", nargs="+")
args = parser.parse_args()
source, output = args.source.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=False)
def hashes():
    return {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in source.rglob("*") if p.is_file()}
before = hashes()
argv = [sys.executable, "-m", "pytest", "-q", "-rA", "-p", "no:cacheprovider",
        "--basetemp", str(output / "temporary-fixtures"),
        "--junitxml", str(output / "junit.xml"), *args.tests]
env = {**os.environ, "PYTHONPATH": str(source), "PYTHONDONTWRITEBYTECODE": "1",
       "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTEST_ADDOPTS": ""}
started = time.monotonic()
with (output / "pytest.stdout").open("wb") as stdout, (output / "pytest.stderr").open("wb") as stderr:
    result = subprocess.run(argv, cwd=source, env=env, stdin=subprocess.DEVNULL,
                            stdout=stdout, stderr=stderr, timeout=55)
after = hashes()
tree = ET.parse(output / "junit.xml")
cases = []
for case in tree.iter("testcase"):
    status = next((tag for tag in ("failure", "error", "skipped") if case.find(tag) is not None), "passed")
    cases.append({"name": case.attrib.get("name"), "class": case.attrib.get("classname"),
                  "status": status})
receipt = {"argv": argv, "source": str(source), "exit_code": result.returncode,
           "elapsed_s": time.monotonic() - started, "python": sys.version,
           "platform": platform.platform(), "pytest": pytest.__version__,
           "canonical_parent": "7f44c4f134f4d56d37dd14c7c2d2aaa3c8c8749e",
           "source_before": before, "source_after": after, "source_unchanged": before == after,
           "cases": cases,
           "raw_logs": {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                        for name in ("pytest.stdout", "pytest.stderr", "junit.xml")}}
(output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"exit_code": result.returncode, "elapsed_s": receipt["elapsed_s"],
                  "counts": {status: sum(c["status"] == status for c in cases)
                             for status in ("passed", "failure", "error", "skipped")},
                  "source_unchanged": before == after, "receipt": str(output / "receipt.json")}))
if before != after:
    raise RuntimeError("native source changed during pytest receiving")
raise SystemExit(result.returncode)
