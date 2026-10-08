#!/usr/bin/env python3
"""Read-only production-source probe using authored native Git/Python fixtures."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

source = Path("/srv/hamon-estate/testpilot-physical-lines-a3425ebf9874")
receiver = Path(__file__).resolve().parent
sys.path.insert(0, str(source))
from testpilot.diff import changed_functions, functions_touching, parse_unified_diff

def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout

def context_case(name, separator, newline):
    repo = receiver / name
    repo.mkdir()
    git(repo, "init", "-q")
    file = repo / "sample.py"
    before = f'note = "left{separator}right"\n\ndef answer():\n    return 1\n'
    after = before.replace("return 1", "return 2")
    file.write_bytes(before.replace("\n", newline).encode())
    git(repo, "add", "sample.py")
    git(repo, "-c", "user.name=Synthetic native fixture", "-c",
        "user.email=fixture@example.invalid", "commit", "-qm", "Authored baseline")
    file.write_bytes(after.replace("\n", newline).encode())
    diff = git(repo, "diff", "--", "sample.py")
    (repo / "change.diff").write_text(diff, encoding="utf-8")
    actual = subprocess.run([sys.executable, "-c",
        "import runpy; print(runpy.run_path('sample.py')['answer']())"],
        cwd=repo, check=True, capture_output=True, text=True).stdout.strip()
    assert actual == "2", "Authored Python source is not executable"
    parsed = parse_unified_diff(diff)
    selected = changed_functions(repo, diff)
    return {"case": name, "source_executes_and_returns": actual,
        "separator_codepoint": ord(separator) if separator else None,
        "newline": repr(newline), "expected_added_lines": [4],
        "actual_added_lines": sorted(parsed[0].added_lines),
        "expected_target": "answer", "actual_targets": [f.qualname for f in selected],
        "target_selected_correctly": [f.qualname for f in selected] == ["answer"],
        "diff": diff}

cases = [
    context_case("unicode_context", "\u2028", "\n"),
    context_case("ordinary_lf", "", "\n"),
    context_case("ordinary_crlf", "", "\r\n"),
]
literal_source = 'def answer():\n    return "left\u2028right"\n'
compile(literal_source, "literal.py", "exec")
selected = functions_touching(literal_source, "literal.py", {2}, {2})
actual_source = selected[0].source
cases.append({"case": "literal_source_slice", "literal_source_compiles": True,
    "expected_source": literal_source.rstrip("\n"), "actual_source": actual_source,
    "source_preserved": actual_source == literal_source.rstrip("\n")})
head = git(source, "rev-parse", "HEAD").strip()
assert head == "47a197fd46b107a797b1547db02cb5ed5ad2abe1"
assert not git(source, "status", "--porcelain").strip(), "Production source changed"
report = {"schema": "hamon.testpilot_physical_line_baseline.v1",
    "python": platform.python_version(), "source_commit": head,
    "diff_module_sha256": hashlib.sha256((source / "testpilot/diff.py").read_bytes()).hexdigest(),
    "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "production_source_unmodified": True, "cases": cases,
    "provider_calls": 0, "model_calls": 0, "pytest_runs": 0}
output = receiver / "baseline-report.json"
output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
print(json.dumps({"report": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    "source_commit": head, "source_sha256": report["diff_module_sha256"],
    "cases": [{k:v for k,v in c.items() if k not in ("diff","expected_source","actual_source")}
              for c in cases], "literal_source_actual": repr(actual_source),
    "source_unmodified": True}, indent=2))
