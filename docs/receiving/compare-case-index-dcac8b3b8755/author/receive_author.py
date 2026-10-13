"""Bounded original/candidate maintained tests for comparison case navigation."""
from pathlib import Path
import argparse, hashlib, json, os, platform, subprocess, sys

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=["original", "candidate"])
args = parser.parse_args()
source = ROOT / args.mode
output = ROOT / ("course-" + args.mode)
output.mkdir()
def identity(path):
    raw = path.read_bytes()
    stat = path.stat()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
            "mode": str(stat.st_mode), "mtime_ns": str(stat.st_mtime_ns), "inode": str(stat.st_ino)}
def inventory(path):
    return {p.relative_to(path).as_posix(): identity(p) if p.is_file() else {"directory": True}
            for p in sorted(path.rglob("*"))}
before = inventory(source)
witness = {str(p): identity(p) for p in (Path(__file__), ROOT / "original-packet.json")}
report = {"schema": "testpilot.case-index-author/1", "mode": args.mode, "python": sys.version,
          "platform": platform.platform(), "pid": os.getpid(), "passed": False,
          "source_before": before, "witness_before": witness,
          "dependency_scope": "pytest8.4.2 and dependencies installed in task-owned dependencies; no report-listed code or provider execution"}
env = dict(os.environ)
env["PYTHONPATH"] = os.pathsep.join((str(ROOT / "dependencies"), str(source)))
env["PYTHONDONTWRITEBYTECODE"] = "1"
env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
selected = ["tests/test_compare_case_index.py"]
if args.mode == "candidate":
    selected += ["tests/test_compare_diagnostics.py",
                 "tests/test_compare.py::test_exact_download_bytes_and_detached_immutable_data",
                 "tests/test_compare.py::test_unknown_junit_does_not_promote_authored_counts_or_incomplete_cost"]
argv = [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", *selected]
try:
    with (output / "pytest.stdout").open("xb") as stdout, (output / "pytest.stderr").open("xb") as stderr:
        child = subprocess.Popen(argv, cwd=source, env=env, stdout=stdout, stderr=stderr)
        report["child"] = {"argv": argv, "pid": child.pid}
        try:
            report["child"]["returncode"] = child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            child.kill()
            report["child"]["returncode"] = child.wait(timeout=10)
            raise
    expected = 1 if args.mode == "original" else 0
    report["expected_returncode"] = expected
    report["passed"] = report["child"]["returncode"] == expected
except Exception as error:
    report["error"] = type(error).__name__ + ": " + str(error)
finally:
    report["source_after"] = inventory(source)
    report["witness_after"] = {str(p): identity(p) for p in (Path(__file__), ROOT / "original-packet.json")}
    report["source_preserved"] = report["source_after"] == before
    report["witness_preserved"] = report["witness_after"] == witness
    report["streams"] = {name: identity(output / name) for name in ("pytest.stdout", "pytest.stderr")}
    report["passed"] = report["passed"] and report["source_preserved"] and report["witness_preserved"]
    (output / "receiving.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"mode": args.mode, "passed": report["passed"], "child": report.get("child"),
                  "source_preserved": report["source_preserved"], "witness_preserved": report["witness_preserved"],
                  "receipt": identity(output / "receiving.json"), "error": report.get("error")}))
raise SystemExit(0 if report["passed"] else 1)

