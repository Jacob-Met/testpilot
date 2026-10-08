"""Independent authored Git fixtures for encoding-owner/physical-line composition.

Git output is explicitly decoded using each fixture's known source encoding.
This receives the text-diff API; it does not claim arbitrary-byte CLI decoding.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--work", type=Path, required=True)
args = parser.parse_args()
args.work.mkdir(parents=True, exist_ok=False)
module_path = args.source / "testpilot/diff.py"
spec = importlib.util.spec_from_file_location("received_diff", module_path)
diff = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = diff
spec.loader.exec_module(diff)
results = []
for name, encoding, prefix, separator, span in (
    ("utf8-bom", "utf-8-sig", "", "\u2028", (3, 4)),
    ("latin1-cookie", "latin-1", "# coding: latin-1\n", "\x85", (4, 5)),
):
    repo = args.work / name
    repo.mkdir()
    def git(*parts):
        return subprocess.run(["git", "-C", str(repo), *parts],
            check=True, capture_output=True).stdout
    git("init", "-q")
    git("config", "core.autocrlf", "false")
    before = prefix + f'note = "left{separator}right"\n\ndef answer():\n    return "left{separator}right", 1\n'
    after = before.replace(", 1", ", 2")
    source_path = repo / "sample.py"
    source_path.write_bytes(before.encode(encoding))
    git("add", "sample.py")
    git("-c", "user.name=Synthetic encoding fixture", "-c",
        "user.email=fixture@example.invalid", "commit", "-qm", "Original")
    source_path.write_bytes(after.encode(encoding))
    raw = source_path.read_bytes()
    namespace = {}
    exec(compile(raw, "sample.py", "exec"), namespace)
    expected = ("left" + separator + "right", 2)
    assert namespace["answer"]() == expected
    raw_patch = git("diff", "HEAD", "--", "sample.py")
    text_patch = raw_patch.decode("utf-8" if encoding == "utf-8-sig" else encoding)
    (repo / "change.diff").write_bytes(raw_patch)
    outcome = {"case": name, "encoding": encoding,
               "input_source_sha256": hashlib.sha256(raw).hexdigest(),
               "git_patch_sha256": hashlib.sha256(raw_patch).hexdigest(),
               "physical_span": list(span)}
    try:
        selected, = diff.changed_functions(repo, text_patch)
        assert (selected.qualname, selected.lineno, selected.end_lineno,
                selected.changed_lines) == ("answer", *span, [span[1]])
        expected_source = f'def answer():\n    return "left{separator}right", 2'
        assert selected.source == expected_source
        reconstructed = {}
        exec(compile(selected.source, "received.py", "exec"), reconstructed)
        assert reconstructed["answer"]() == expected
        outcome["passed"] = True
        outcome["selected"] = selected.to_dict()
    except Exception as error:
        outcome.update(passed=False, exception=type(error).__name__, message=str(error))
    assert source_path.read_bytes() == raw
    results.append(outcome)
receipt = {"schema": "hamon.testpilot.encoding_composition_receiving.v1",
           "source_commit": subprocess.check_output(["git", "-C", str(args.source),
                                                      "rev-parse", "HEAD"], text=True).strip(),
           "source_sha256": hashlib.sha256(module_path.read_bytes()).hexdigest(),
           "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "python": sys.version, "tests": len(results),
           "passed": sum(item["passed"] for item in results),
           "failed": sum(not item["passed"] for item in results),
           "results": results,
           "scope": "Actual Git text-diff API with explicitly decoded authored fixtures; no provider, install or byte-decoding claim"}
(args.work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
raise SystemExit(int(receipt["failed"] > 0))
