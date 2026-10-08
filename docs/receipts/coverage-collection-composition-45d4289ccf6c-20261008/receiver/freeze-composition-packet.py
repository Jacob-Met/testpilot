"""Freeze compact evidence without rerunning tests or changing product source."""
from collections import Counter
from datetime import datetime, timezone
import hashlib, json, shutil, subprocess, xml.etree.ElementTree as ET
from pathlib import Path

root=Path("/home/jacob/testpilot-coverage-45d4289ccf6c")
evidence=root/"composition-dcd353-evidence"
source=root/"composition-dcd353-worktree"
packet=evidence/"handoff-packet"
assert not packet.exists()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def jread(p): return json.loads(p.read_text())
tree=subprocess.check_output(["git","-C",str(source),"write-tree"],text=True).strip()
assert tree=="08d13653668d58660cbf3614108ba79ddd8f3b17"
subprocess.run(["git","-C",str(source),"diff","--quiet"],check=True)
full=jread(evidence/"full-suite/receipt.json")
four=jread(evidence/"selected-python-aligned/receipt.json")
assert full["source_sha256"]==four["source_sha256"]
assert full["source_unchanged"] and four["source_unchanged"]
assert full["sandbox_temporary_children_after"]==four["sandbox_temporary_children_after"]==[]
expected_failed={"test_project_environment_runs_baseline_generation_and_repair["+s+"]" for s in ("absolute","relative","path","symlink-parent")}
assert {c["name"] for c in full["cases"] if c["outcome"]=="failed"}==expected_failed
assert {c["name"] for c in four["cases"]}==expected_failed
assert Counter(c["outcome"] for c in full["cases"])=={"passed":165,"failed":4}
assert Counter(c["outcome"] for c in four["cases"])=={"passed":4}
for phase,receipt in (("full-suite",full),("selected-python-aligned",four)):
    raw=[]
    for case in ET.parse(evidence/phase/"junit.xml").iter("testcase"):
        outcome=next((label for tag,label in (("failure","failed"),("error","error"),("skipped","skipped")) if case.find(tag) is not None),"passed")
        raw.append({"name":case.get("name"),"outcome":outcome})
    assert raw==receipt["cases"],phase
rows=[]
copies=[]
for phase in ("full-suite","selected-python-aligned"):
    for i,spelling in enumerate(("absolute","relative","path","symlink-parent")):
        fixture=evidence/phase/"fixtures"/("test_project_environment_runs_"+str(i))
        assert fixture.is_dir() and not fixture.is_symlink()
        report_path=fixture/"output/report.json"
        report=jread(report_path)
        executions=[json.loads(line) for line in (fixture/"executions.jsonl").read_text().splitlines()]
        final=report["final"]
        environment=fixture/"physical/prepared environment"
        assert report["status"]=="passed" and report["repair_rounds_used"]==report["tests_written"]==1
        assert report["rounds"][0]["result"]["failed"]==1
        assert final["passed"]==2 and final["failed"]==final["errors"]==final["skipped"]==0
        assert final["generated_files"]==["tests/test_adjusted.py"] and final["junit_available"] is True
        assert final["generated"]=={"collected":1,"passed":1,"failed":0,"error":0,"skipped":0}
        assert len(executions)==5 and Counter(item["label"] for item in executions)=={"existing":3,"generated":2}
        assert all(item["prefix"]==str(environment) and item["executable"]==str(environment/"bin/python") for item in executions)
        if phase=="full-suite":
            assert report["coverage"] is None
        else:
            assert report["coverage"]=={"total_before":100.0,"total_after":100.0,"total_delta":0.0,"changed_lines_executable":2,"changed_lines_before":100.0,"changed_lines_after":100.0}
        fixture_files=("output/report.json","output/report.md","output/testpilot.patch","executions.jsonl","physical/prepared environment/pyvenv.cfg","physical/prepared environment/lib/python3.14/site-packages/test-tooling.pth","project source/subject.py","project source/tests/test_existing.py")
        entries=[]
        for rel in fixture_files:
            path=fixture/rel
            assert path.is_file(),path
            target=Path("selected-cli")/phase/spelling/rel.replace("prepared environment","prepared-environment").replace("project source","project-source")
            copies.append((path,target))
            entries.append({"fixture_path":rel,"packet_path":target.as_posix(),"sha256":sha(path),"bytes":path.stat().st_size})
        rows.append({"phase":phase,"spelling":spelling,"coverage":report["coverage"],"status":report["status"],"repair_rounds_used":report["repair_rounds_used"],"final_passed":2,"generated_collected":1,"generated_passed":1,"junit_available":True,"selected_interpreter_executions":5,"source_and_tests_unchanged":True,"files":entries})
assert len({row["files"][2]["sha256"] for row in rows})==1
assert len({row["files"][6]["sha256"] for row in rows})==1
assert len({row["files"][7]["sha256"] for row in rows})==1
summary={
    "schema":"testpilot-prospective-composition-receiving/1",
    "utc":datetime.now(timezone.utc).isoformat(),
    "source_tree":tree,
    "coverage_parent":"fd77eb028bdbdba35644b44c524471b6413fad39",
    "owner_parent":"dcd353531ad3dde353b63db4b09adca976b9f256",
    "qualification":"Prospective native composition is supported by one 165-pass/4-failure full run and an environment-only correction with all four affected controls passing. This is not a single-environment 169-pass run, hosted acceptance, or disposition of owner86776/receiver965d review.",
    "source_changes_between_runs":False,
    "initial_full_gate":{"exit":full["exit"],"passed":165,"failed":4,"errors":0,"skips":0,"receipt_sha256":sha(evidence/"full-suite/receipt.json")},
    "bounded_corrected_gate":{"exit":four["exit"],"passed":4,"failed":0,"errors":0,"skips":0,"receipt_sha256":sha(evidence/"selected-python-aligned/receipt.json")},
    "full_gate_source_and_receiving":"15 complete configured test modules, including seven coverage tests and 26 owner/independent generated collection tests. The four failures were the existing selected-Python fixture's coverage assertion.",
    "environment_diagnosis_sha256":sha(evidence/"selected-python-tooling-diagnosis.json"),
    "aligned_tooling_manifest_sha256":sha(evidence/"aligned-tooling-manifest.json"),
    "both_sandbox_temporary_directories_empty":True,
    "selected_cli":rows,
    "future_integration_conditions":["Current owner86776 source and receiver965d disposition","Composition against the actual accepted integration head","Existing hosted CI on the published final head"],
}
summary_path=evidence/"composition-receiving-summary.json"
assert not summary_path.exists()
summary_path.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
packet.mkdir()
for path in sorted(evidence.iterdir()):
    if path.is_file():
        shutil.copyfile(path,packet/path.name)
for phase in ("full-suite","selected-python-aligned"):
    for name in ("receipt.json","junit.xml","stdout.txt","stderr.txt"):
        target=packet/phase/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(evidence/phase/name,target)
for path,relative in copies:
    target=packet/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(path,target)
shutil.copyfile(root/"run_receiving.py",packet/"run_receiving.py")
payload=[{"path":p.relative_to(packet).as_posix(),"sha256":sha(p),"bytes":p.stat().st_size} for p in sorted(packet.rglob("*")) if p.is_file()]
manifest={"schema":"testpilot-prospective-composition-payload/1","source_tree":tree,"files":payload,"note":"Frozen initial receiver packet, prior to the independent reviewer addendum. Every original negative remains unchanged."}
manifest_path=packet/"artifact-manifest.json"
manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
print(json.dumps({"packet":str(packet),"payload_files":len(payload),"payload_bytes":sum(p["bytes"] for p in payload),"manifest_sha256":sha(manifest_path),"summary_sha256":sha(summary_path),"source_tree":tree},indent=2))
