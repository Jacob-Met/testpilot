from pathlib import Path
import hashlib,json,os,platform,shutil,subprocess,sys,tempfile,time
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parent
variant=sys.argv[1]
source=ROOT/variant
assert variant in ("baseline","candidate") and (source/"testpilot/__main__.py").is_file()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source_before={str(p.relative_to(source)):digest(p) for p in sorted(source.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}
fixture=Path(tempfile.mkdtemp(prefix=variant+"-fixtures-",dir=ROOT))
repo=fixture/"repo";repo.mkdir()
(repo/"api.py").write_text("def answer():\n    return 42\n",encoding="utf-8")
diff=fixture/"empty.diff";diff.write_bytes(b"")
script=fixture/"script";script.mkdir()
(script/"01-unused.txt").write_text("Authored unused response: no changed functions.\n",encoding="utf-8")
inputs=[repo/"api.py",diff,script/"01-unused.txt"]
input_before={str(p.relative_to(fixture)):digest(p) for p in inputs}
env=dict(os.environ,PYTHONPATH=str(source),PYTHONDONTWRITEBYTECODE="1")
report={"schema":"hamon.independent_testpilot_timeout_admission.v1","worker":"estate-f5c43297f890/estate_coordination",
"variant":variant,"base_commit":"cec50d8df4499ba509615e179d82ef3861379bd2","started_at":datetime.now(timezone.utc).isoformat(),
"python":sys.version,"platform":platform.platform(),"source_before":source_before,"checks":[]}
def keep(check,actual,passed):
    report["checks"].append({"name":check,"actual":actual,"passed":bool(passed)})
def command(out,diff_value=None,timeout=None):
    c=[sys.executable,"-B","-m","testpilot","run","--repo",str(repo),"--diff",str(diff) if diff_value is None else diff_value,
       "--backend","scripted","--script",str(script),"--out",str(out)]
    if timeout is not None:c.append("--timeout="+timeout)
    return c
names=("testpilot.patch","report.json","report.md","report.html")
sentinel={n:("Previous "+n+" must survive invalid admission.\n").encode() for n in names}
def existing_output(tag):
    out=fixture/tag;out.mkdir()
    for n,b in sentinel.items():(out/n).write_bytes(b)
    return out
def unchanged(out):
    return sorted(p.name for p in out.iterdir())==sorted(names) and all((out/n).read_bytes()==b for n,b in sentinel.items())

for i,value in enumerate(("NaN","+INFINITY","-inf","1e309","-0.0","-3.25","1e-9999")):
    out=existing_output("invalid-"+str(i))
    p=subprocess.run(command(out,timeout=value),env=env,cwd=fixture,capture_output=True,text=True,timeout=6)
    same=unchanged(out)
    keep("invalid_preserves_previous_output:"+value,{"argv":p.args,"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr,"previous_output_unchanged":same},
         p.returncode==2 and "--timeout" in p.stderr and "Traceback" not in p.stderr and same)

# Existing malformed-number refusal remains a control.
out=existing_output("lexical-invalid")
p=subprocess.run(command(out,timeout="not-a-duration"),env=env,cwd=fixture,capture_output=True,text=True,timeout=6)
keep("existing_lexical_refusal",{"returncode":p.returncode,"stderr":p.stderr,"previous_output_unchanged":unchanged(out)},
     p.returncode==2 and unchanged(out))

# Every positive finite float remains admitted, including subnormal/large bounds.
for i,value in enumerate((None,"5e-324","1e-300"," 0.125 ","+1e2","1.7976931348623157e308","1_000")):
    out=fixture/("valid-"+str(i))
    p=subprocess.run(command(out,timeout=value),env=env,cwd=fixture,capture_output=True,text=True,timeout=6)
    parsed=json.loads((out/"report.json").read_text()) if (out/"report.json").exists() else None
    keep("finite_or_default_admitted:"+str(value),{"argv":p.args,"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr,"result":parsed},
         p.returncode==1 and parsed is not None and parsed["status"]=="no_changes" and not parsed["ledger"].get("entries")
         and parsed["final"] is None and not parsed["test_files"])

# Actual stdin remains open: admission must finish before reading the requested diff.
for i,value in enumerate(("nan","0")):
    out=existing_output("open-stdin-"+str(i))
    argv=command(out,diff_value="-",timeout=value)
    started=time.monotonic()
    p=subprocess.Popen(argv,env=env,cwd=fixture,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    completed_without_eof=True
    try:
        p.wait(timeout=2)
    except subprocess.TimeoutExpired:
        completed_without_eof=False
        p.kill() # Only this own child; the current CLI is still waiting at _read_diff.
        p.wait(timeout=2)
    stdout,stderr=p.communicate()
    same=unchanged(out)
    keep("invalid_refuses_without_stdin_eof:"+value,
         {"argv":argv,"returncode":p.returncode,"stdout":stdout,"stderr":stderr,"elapsed":time.monotonic()-started,
          "completed_without_eof":completed_without_eof,"own_waiting_child_killed":not completed_without_eof,"previous_output_unchanged":same},
         completed_without_eof and p.returncode==2 and "--timeout" in stderr and same)

for explicit in (False,True):
    argv=[sys.executable,"-B","-m","testpilot","targets","--repo",str(repo),"--diff",str(diff),"--json"]
    if explicit:argv+=["--target","api.py::answer"]
    p=subprocess.run(argv,env=env,cwd=fixture,capture_output=True,text=True,timeout=6)
    parsed=json.loads(p.stdout) if p.returncode==0 else None
    functions=parsed.get("changed_functions",[]) if parsed is not None else []
    keep("existing_targets:"+str(explicit),{"argv":argv,"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr},
         p.returncode==0 and len(functions)==(1 if explicit else 0) and (not explicit or functions[0]["qualname"]=="answer"))

out=fixture/"recheck-invalid"
argv=[sys.executable,"-B","-m","testpilot","recheck","--repo",str(repo),"--report",str(fixture/"valid-0/report.json"),
      "--out",str(out),"--timeout=nan"]
p=subprocess.run(argv,env=env,cwd=fixture,capture_output=True,text=True,timeout=6)
keep("existing_recheck_refusal",{"argv":argv,"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr,"output_absent":not out.exists()},
     p.returncode==2 and "Traceback" not in p.stderr and not out.exists())

report["inputs_unchanged"]=all(digest(p)==input_before[str(p.relative_to(fixture))] for p in inputs)
report["source_after"]={str(p.relative_to(source)):digest(p) for p in sorted(source.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}
report["source_unchanged"]=report["source_before"]==report["source_after"]
report["passed"]=sum(c["passed"] for c in report["checks"]);report["failed"]=len(report["checks"])-report["passed"]
report["finished_at"]=datetime.now(timezone.utc).isoformat()
shutil.rmtree(fixture)
report["private_fixtures_removed"]=True
report["scope"]="Actual module CLI subprocesses, authored empty diff/input/output only. No pytest/model execution needed; no provider or live developer repository. Stdin controls kill only own child known to be waiting before backend construction."
receipt=ROOT/(variant+"-receipt.json")
receipt.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"variant":variant,"receipt_path":str(receipt),"receipt_sha256":digest(receipt),
"receiver_sha256":digest(Path(__file__)),"passed":report["passed"],"failed":report["failed"],
"source_unchanged":report["source_unchanged"],"inputs_unchanged":report["inputs_unchanged"],
"checks":[{"name":x["name"],"passed":x["passed"],"returncode":x["actual"]["returncode"]} for x in report["checks"]]},indent=2))
