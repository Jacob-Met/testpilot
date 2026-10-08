"""Actual CLI witnesses for raw Git diff transport; authored fixtures only."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

PACKAGE = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
OUT.mkdir(parents=True, exist_ok=False)
ENV = {
    "PATH": os.defpath,
    "LANG": "C.UTF-8",
    "PYTHONDONTWRITECODE": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONPATH": str(PACKAGE),
    "TMPDIR": str(OUT),
}
PYTHON = sys.argv[3] if len(sys.argv) > 3 else sys.executable

def command(argv, cwd=None, data=None):
    return subprocess.run(argv, cwd=cwd, env=ENV, input=data, capture_output=True, timeout=30)

def git(repo, *args):
    p = command(["git", "-C", str(repo), *args])
    if p.returncode:
        raise RuntimeError(p.stderr.decode("utf-8", "backslashreplace"))
    return p.stdout

def digest(b):
    return hashlib.sha256(b).hexdigest()

def files(root):
    return {str(p.relative_to(root)): digest(p.read_bytes())
            for p in sorted(root.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts}

source_before = {str(p.relative_to(PACKAGE)): digest(p.read_bytes())
                 for p in sorted((PACKAGE / "testpilot").glob("*.py"))}
rows = []
for name, codec, label in [
    ("utf8", "utf-8", "café"),
    ("latin1", "latin-1", "café"),
    ("cp1252", "cp1252", "€"),
]:
    case = OUT / name
    repo = case / "project"
    repo.mkdir(parents=True)
    before = '# coding: ' + codec + '\nLABEL = ' + repr(label) + '\n\ndef value():\n    return 1\n'
    subject = repo / "subject.py"
    subject.write_bytes(before.encode(codec))
    git(repo, "init", "-q")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=TestPilot Fixture", "-c",
        "user.email=testpilot-fixture@invalid.local", "-c", "commit.gpgsign=false",
        "commit", "-qm", "before")
    subject.write_bytes(before.replace("return 1", "return 2").encode(codec))
    raw = git(repo, "diff", "HEAD", "--", "*.py")
    (case / "change.diff").write_bytes(raw)
    original_files = files(repo)
    namespace = {}
    exec(compile(subject.read_bytes(), str(subject), "exec"), namespace)
    assert namespace["value"]() == 2
    assert namespace["LABEL"] == label
    script = case / "script"
    script.mkdir()
    (script / "01.txt").write_text("Check the changed value.", encoding="utf-8")
    fence = chr(96) * 3
    (script / "02.txt").write_text(
        fence + "python path=tests/test_subject_generated.py\nfrom subject import value\n\n"
        "def test_value():\n    assert value() == 2\n" + fence + "\n", encoding="utf-8")
    case_row = {"case": name, "source_codec": codec, "source_sha256": digest(subject.read_bytes()),
                "diff_sha256": digest(raw), "raw_diff_has_non_utf8": False, "observations": []}
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        case_row["raw_diff_has_non_utf8"] = True
    for operation in ("targets", "run"):
        for route in ("git", "file", "stdin"):
            args = [PYTHON, "-B", "-m", "testpilot", operation, "--repo", str(repo)]
            if route == "git":
                args += ["--git-base", "HEAD"]
            else:
                args += ["--diff", "-" if route == "stdin" else str(case / "change.diff")]
            destination = case / f"{operation}-{route}"
            if operation == "targets":
                args += ["--json"]
            else:
                args += ["--backend", "scripted", "--script", str(script), "--rounds", "0",
                         "--timeout", "15", "--python", PYTHON, "--out", str(destination)]
            p = command(args, data=raw if route == "stdin" else None)
            (case / f"{operation}-{route}.stdout").write_bytes(p.stdout)
            (case / f"{operation}-{route}.stderr").write_bytes(p.stderr)
            row = {"operation": operation, "route": route, "returncode": p.returncode,
                   "stdout_sha256": digest(p.stdout), "stderr_sha256": digest(p.stderr),
                   "unicode_decode_error": b"decode" in p.stderr,
                   "traceback": b"Traceback" in p.stderr}
            report = destination / "report.json"
            if report.exists():
                data = json.loads(report.read_text(encoding="utf-8"))
                row.update(status=data["status"], tests_written=data["tests_written"],
                           final_summary=(data["final"] or {}).get("summary"),
                           selected=data["changed_functions"],
                           ledger_calls=sum(v["calls"] for v in data["ledger"]["by_model"].values()))
            elif operation == "targets" and p.returncode == 0:
                row["selected"] = json.loads(p.stdout)["changed_functions"]
            case_row["observations"].append(row)
    case_row["inputs_unchanged"] = original_files == files(repo)
    assert case_row["inputs_unchanged"]
    rows.append(case_row)
source_after = {str(p.relative_to(PACKAGE)): digest(p.read_bytes())
                for p in sorted((PACKAGE / "testpilot").glob("*.py"))}
assert source_before == source_after
receipt = {"source": subprocess.check_output(["git", "-C", str(PACKAGE), "rev-parse", "HEAD"], text=True).strip(),
           "python": PYTHON, "runtime": sys.version, "source_files": source_before,
           "source_unchanged": True, "cases": rows}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
print(json.dumps({"receipt_sha256": digest((OUT / "receipt.json").read_bytes()),
                  "source": receipt["source"], "cases": [
    {"case": r["case"], "non_utf8": r["raw_diff_has_non_utf8"],
     "outcomes": [{k:v for k,v in o.items() if k in
                  ("operation","route","returncode","traceback","status","tests_written","final_summary")}
                  for o in r["observations"]]} for r in rows]}, indent=2))
