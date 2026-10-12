#!/usr/bin/env python3
"""Independent bounded receiver for TestPilot function-line indexing.

freeze reads only an original source root; compare reads the proposed root only
after the fixture and complete original output files have been written.
"""
from __future__ import annotations
import argparse
import dataclasses
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time


LINES = [
    "@deco(",
    "    'Ω',",
    ")",
    "def outer(x):",
    "    def inner():",
    "        return 'inner'",
    "    return inner()",
    "",
    "class Box:",
    "    @classmethod",
    "    async def go(cls):",
    "        return 'x\u2028y'",
    "",
    "if True:",
    "    def shadow():",
    "        return 1",
    "else:",
    "    def shadow():",
    "        return 2",
    "try:",
    "    pass",
    "except Exception:",
    "    def caught():",
    "        return 3",
    "finally:",
    "    def finished():",
    "        return 4",
    "match 0:",
    "    case 0:",
    "        def branch():",
    "            return 5",
]
SPANS = [
    ("outer", 1, 7, False), ("Box.go", 10, 12, True),
    ("shadow", 15, 16, False), ("shadow", 18, 19, False),
    ("finished", 26, 27, False), ("caught", 23, 24, False),
    ("branch", 30, 31, False),
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def load_module(root: Path):
    path = root / "testpilot/diff.py"
    spec = importlib.util.spec_from_file_location("receiving_diff", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def fixture_cases() -> list[dict]:
    cases = []
    rng = random.Random(7920261012)
    for ending in ["\n", "\r\n", "\r"]:
        source = ending.join(LINES) + ending
        for line in range(-2, 35):
            cases.append({"name": repr(ending) + "/single/" + str(line), "source": source,
                "path": "pkg/fixture.py", "lines": [line], "added": [line-1, line, line+1],
                "literal": True})
        for n in range(18):
            cases.append({"name": repr(ending) + "/sparse/" + str(n), "source": source,
                "path": "pkg/fixture.py", "lines": rng.sample(range(-5, 40), rng.randrange(0, 20)),
                "added": rng.sample(range(-5, 40), rng.randrange(0, 20)), "literal": True})
        cases.append({"name": repr(ending)+"/all", "source": source, "path": "pkg/__init__.py",
            "lines": list(range(-1, 35)), "added": list(range(-1, 35)), "literal": True})
    for name, source, lines, added in [
        ("no-functions", "value = 10\n", [1], [1]),
        ("empty-source", "", [0, 1, 2], [-1, 1, 3]),
        ("huge-integers", "def f():\n    return 1\n", [-10**100, 10**100, 2], [-10**100, 1, 10**100]),
        ("touch-empty", "def f():\n    return 1\n", [], [1, 2]),
        ("added-empty", "def f():\n    return 1\n", [1], []),
        ("invalid-source", "def broken(\n", [1], [1]),
        ("invalid-source-empty", "def broken(\n", [], []),
        ("non-python-file-name", "def f():\n    return 1\n", [1], [2]),
    ]:
        cases.append({"name": name, "source": source, "path": "fixture λ.py" if name != "non-python-file-name" else "README.txt",
            "lines": lines, "added": added, "literal": False})
    return cases


def results(root: Path, cases: list[dict]) -> dict:
    mod = load_module(root)
    outcomes = []
    for case in cases:
        lines = set(case["lines"])
        added = set(case["added"])
        before = (lines.copy(), added.copy(), case["source"])
        try:
            output = [x.to_dict() for x in mod.functions_touching(case["source"], case["path"], lines, added)]
            outcome = {"name": case["name"], "output": output}
        except Exception as e:
            outcome = {"name": case["name"], "error": {"type": type(e).__name__, "text": str(e),
                "lineno": getattr(e, "lineno", None), "offset": getattr(e, "offset", None),
                "end_lineno": getattr(e, "end_lineno", None), "end_offset": getattr(e, "end_offset", None)}}
        assert (lines, added, case["source"]) == before, "input mutation"
        if case["literal"]:
            expected = []
            for name, start, end, is_method in SPANS:
                if any(start <= line <= end for line in lines):
                    expected.append({"path": case["path"], "module": "pkg" if case["path"].endswith("/__init__.py") else "pkg.fixture",
                        "qualname": name, "lineno": start, "end_lineno": end,
                        "changed_lines": sorted(line for line in added if start <= line <= end),
                        "source": "\n".join(LINES[start-1:end]), "is_method": is_method})
            assert outcome.get("output") == expected, "hand-authored span/record mismatch: " + case["name"]
        outcomes.append(outcome)
    return {"source_root": str(root), "production_sha256": sha((root/"testpilot/diff.py").read_bytes()),
        "cases": outcomes, "case_count": len(outcomes), "literal_count": sum(x["literal"] for x in cases)}


def cli_fixture(directory: Path) -> list[dict]:
    repo = directory / "consumer"
    (repo/"pkg").mkdir(parents=True)
    source = "\n".join(LINES) + "\n"
    (repo/"pkg/sample.py").write_bytes(source.encode())
    variants = [
        ("two-targets", source.replace("    return inner()", "    return None").replace("@classmethod", "@staticmethod"), ["outer", "Box.go"], [[7], [10]]),
        ("deletion-anchor", source.replace("    return inner()", "    marker = 1\n    return inner()"), ["outer"], [[]]),
        ("class-header", source.replace("class Box:", "class Box(object):"), [], []),
        ("empty", source, [], []),
    ]
    out = []
    for name, old, names, changes in variants:
        # Only LF splits count as physical lines; the source deliberately has U+2028.
        diff = "".join(difflib.unified_diff([x+"\n" for x in old[:-1].split("\n")],
            [x+"\n" for x in source[:-1].split("\n")], fromfile="a/pkg/sample.py", tofile="b/pkg/sample.py"))
        (directory/(name+".diff")).write_bytes(diff.encode())
        out.append({"name":name,"expected_names":names,"expected_changed_lines":changes})
    return out


def run_cli(root: Path, directory: Path, cases: list[dict], label: str) -> list[dict]:
    env = dict(os.environ, PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE="1")
    outputs = []
    source = directory/"consumer/pkg/sample.py"
    before = source.read_bytes()
    for case in cases:
        diff = directory/(case["name"]+".diff")
        for stdin in [False, True]:
            argv = [sys.executable, "-B", "-m", "testpilot", "targets", "--repo", str(directory/"consumer"),
                "--diff", "-" if stdin else str(diff), "--json"]
            p = subprocess.run(argv, cwd=root, env=env, input=diff.read_bytes() if stdin else None,
                capture_output=True, timeout=30)
            name = case["name"] + ("-stdin" if stdin else "-file")
            (directory/(label+"-"+name+".stdout.txt")).write_bytes(p.stdout)
            (directory/(label+"-"+name+".stderr.txt")).write_bytes(p.stderr)
            assert p.returncode == 0, (name, p.returncode, p.stderr.decode())
            value = json.loads(p.stdout)
            records = value if isinstance(value,list) else value.get("changed_functions",value.get("functions"))
            assert records is not None, value
            assert [r["qualname"] for r in records] == case["expected_names"], (name, value)
            assert [r["changed_lines"] for r in records] == case["expected_changed_lines"], (name, value)
            assert source.read_bytes() == before, "CLI changed source"
            outputs.append({"name":name,"argv":argv,"exit":p.returncode,"stdout":p.stdout.decode(),"stderr":p.stderr.decode()})
    return outputs


def main():
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=["freeze","compare"])
    p.add_argument("--source-root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    root=a.source_root.resolve(); directory=a.out.resolve()
    if a.mode=="freeze":
        directory.mkdir(exist_ok=False)
        cases=fixture_cases()
        write(directory/"frozen-fixtures.json",cases)
        cli_cases=cli_fixture(directory)
        write(directory/"cli-cases.json",cli_cases)
        result=results(root,cases)
        write(directory/"original-results.json",result)
        cli=run_cli(root,directory,cli_cases,"original")
        write(directory/"original-cli.json",cli)
        write(directory/"freeze.json",{"created_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
            "receiver_sha256":sha(Path(__file__).read_bytes()),
            "fixtures_sha256":sha((directory/"frozen-fixtures.json").read_bytes()),
            "original_results_sha256":sha((directory/"original-results.json").read_bytes()),
            "original_cli_sha256":sha((directory/"original-cli.json").read_bytes()),
            "candidate_source_read":False,"api_cases":result["case_count"],"literal_cases":result["literal_count"],"cli_invocations":len(cli)})
        print(json.dumps({"frozen":True,"api_cases":result["case_count"],"literal_cases":result["literal_count"],"cli_invocations":len(cli)}))
    else:
        cases=json.loads((directory/"frozen-fixtures.json").read_text())
        frozen=json.loads((directory/"freeze.json").read_text())
        assert sha(Path(__file__).read_bytes())==frozen["receiver_sha256"],"receiver changed after freeze"
        assert sha((directory/"frozen-fixtures.json").read_bytes())==frozen["fixtures_sha256"],"fixtures changed"
        original=json.loads((directory/"original-results.json").read_text())
        result=results(root,cases)
        write(directory/"candidate-results.json",result)
        assert result["cases"]==original["cases"],"candidate result/exception differs"
        cli=run_cli(root,directory,json.loads((directory/"cli-cases.json").read_text()),"candidate")
        write(directory/"candidate-cli.json",cli)
        original_cli=json.loads((directory/"original-cli.json").read_text())
        assert [(r["name"],r["exit"],r["stdout"],r["stderr"]) for r in cli] == [(r["name"],r["exit"],r["stdout"],r["stderr"]) for r in original_cli],"CLI outcome differs"
        receipt={"accepted":True,"api_cases":len(cases),"literal_cases":result["literal_count"],"cli_invocations_per_source":len(cli),
            "candidate_sha256":result["production_sha256"],"original_sha256":original["production_sha256"],
            "all_complete_records_equal":True,"all_cli_bytes_equal":True,"all_source_inputs_unchanged":True,
            "freeze":frozen,"scope":"Normal integer set inputs; original source and CLI contract read before candidate source or candidate tests. No full-suite rerun, empirical performance generalization, or installed adoption claim."}
        write(directory/"independent-receipt.json",receipt)
        print(json.dumps(receipt,indent=2))


if __name__=="__main__":main()
