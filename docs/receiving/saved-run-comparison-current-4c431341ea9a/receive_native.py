"""Produce two current native reports and receive their portable comparison."""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


BASE = "c32b5459657ec26aac9837b823b1bc326510873e"
DONOR = "a978524a75bb53d9beaa2e271b187069deafb800"
SOURCE = Path(__file__).resolve().parents[3]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new receiving directory")
    args = parser.parse_args()
    output = args.out.resolve()
    output.mkdir(parents=False, exist_ok=False)
    environment = dict(os.environ, PYTHONPATH=str(SOURCE), PYTHONDONTWRITEBYTECODE="1",
                       TESTPILOT_BACKEND="receiving-must-not-call-a-provider")
    receipt = {
        "schema": "testpilot.comparison-current-receiving/1",
        "base_commit": BASE,
        "donor_pr": "https://github.com/Jacob-Met/testpilot/pull/33",
        "donor_commit": DONOR,
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=SOURCE, text=True).strip(),
        "python": sys.version,
        "packages": {name: importlib.metadata.version(name) for name in ("pytest", "coverage")},
        "source_sha256": {name: sha(SOURCE / name) for name in (
            "testpilot/__main__.py", "testpilot/compare.py", "testpilot/compare_html.py",
            "testpilot/loop.py", "testpilot/model.py", "testpilot/sandbox.py")},
        "commands": [],
    }

    def run(arguments: list[str]) -> None:
        command = [sys.executable, "-B", "-m", "testpilot", *arguments]
        started = time.monotonic()
        result = subprocess.run(command, cwd=SOURCE, env=environment,
                                capture_output=True, text=True, timeout=90)
        receipt["commands"].append({"command": command, "returncode": result.returncode,
                                    "seconds": time.monotonic() - started,
                                    "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode:
            raise RuntimeError(f"native command refused: {result.stderr}")

    try:
        reports = []
        for kind in ("pure-deletion", "measured"):
            project = output / kind / "project"
            scripts = output / kind / "script"
            project.mkdir(parents=True)
            scripts.mkdir()
            (project / "tests").mkdir()
            (project / "calc.py").write_text("def answer():\n    return 7\n")
            (project / "tests/test_existing.py").write_text(
                "import calc\n\ndef test_existing():\n    assert callable(calc.answer)\n")
            (scripts / "01-plan.md").write_text("Check the recorded answer.\n")
            (scripts / "02-tests.md").write_text(
                "```python path=tests/test_answer.py\nfrom calc import answer\n\n"
                "def test_answer():\n    assert answer() == 7\n```\n")
            diff = output / kind / "change.diff"
            diff.write_text("--- a/calc.py\n+++ b/calc.py\n" + (
                "@@ -1,3 +1,2 @@\n def answer():\n-    obsolete = 1\n     return 7\n"
                if kind == "pure-deletion" else
                "@@ -1,2 +1,2 @@\n def answer():\n-    return 6\n+    return 7\n"))
            original = {str(p.relative_to(project)): sha(p) for p in project.rglob("*") if p.is_file()}
            results = output / kind / "result"
            run(["run", "--repo", str(project), "--diff", str(diff), "--backend", "scripted",
                 "--script", str(scripts), "--rounds", "0", "--timeout", "15",
                 "--python", sys.executable, "--out", str(results)])
            report = results / "report.json"
            data = json.loads(report.read_bytes())
            if data["status"] != "passed" or data["final"]["generated"]["passed"] != 1:
                raise RuntimeError("native report lacks a passing generated case")
            if kind == "pure-deletion":
                if (data["coverage"]["changed_lines_before"] is not None
                        or data["coverage"]["changed_lines_after"] is not None):
                    raise RuntimeError("pure deletion did not exercise the nullable producer fields")
            elif (data["coverage"]["changed_lines_before"] != 0.0
                  or data["coverage"]["changed_lines_after"] != 100.0):
                raise RuntimeError("measured control did not retain native zero and measured coverage")
            if original != {str(p.relative_to(project)): sha(p) for p in project.rglob("*") if p.is_file()}:
                raise RuntimeError("native run changed its input project")
            reports.append(report)

        inputs = [path.read_bytes() for path in reports]
        comparison = output / "comparison.html"
        run(["compare", "--before", str(reports[0]), "--after", str(reports[1]),
             "--out", str(comparison)])
        page = comparison.read_text()
        downloads = re.findall(r'href="data:application/json;base64,([^"]+)"', page)
        if [base64.b64decode(data) for data in downloads] != inputs:
            raise RuntimeError("comparison downloads changed the original report bytes")
        if [path.read_bytes() for path in reports] != inputs or "None%" in page:
            raise RuntimeError("comparison changed its inputs or rendered missing percentages as numbers")
        for label in ("Changed lines before generation", "Changed lines after generation"):
            row = re.search(r"<tr><td>" + label + r"</td>.*?</tr>", page).group()
            if row.count(">Unavailable<") != 1:
                raise RuntimeError("comparison did not keep unavailable and measured coverage distinct")
        receipt["artifacts"] = [
            {"path": str(path.relative_to(output)), "bytes": path.stat().st_size, "sha256": sha(path)}
            for path in [*reports, comparison]
        ]
        receipt["passed"] = True
    except Exception as exc:
        receipt["passed"] = False
        receipt["error"] = str(exc)
        raise
    finally:
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"passed": True, "receipt": str(output / "receipt.json"),
                      "comparison": str(comparison)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
