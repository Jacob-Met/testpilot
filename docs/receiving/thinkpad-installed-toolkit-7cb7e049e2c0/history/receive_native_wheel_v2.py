"""Continue the verified install after correcting only the receiver's version-text expectation."""
from datetime import datetime,timezone
import hashlib,importlib.metadata,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
prior=json.loads((ROOT/"native_receiving.json").read_text())
assert prior["status"]=="failed" and prior["error"]=="AssertionError: testpilot 0.1.0\n"
assert [x["name"] for x in prior["commands"]]==["environment","install","version"]
assert all(x["exit_code"]==0 for x in prior["commands"])
payload=json.loads((ROOT/"native_payload_v1.json").read_text())
ENV=ROOT/"venv";PY=ENV/"bin/python";purelib=Path(prior["environment"]["purelib"])
assert purelib.is_relative_to(ENV) and not (ROOT/"course-v1").exists()
assert (ROOT/"version.stdout").read_text().strip()=="testpilot 0.1.0"
receipt={k:v for k,v in prior.items() if k not in ["status","error","completed_utc","started_utc","commands"]}
receipt.update(status="started",started_utc=datetime.now(timezone.utc).isoformat(),commands=[],prior_receipt="native_receiving.json",harness_correction="Initial receiver expected bare 0.1.0; the actual correct CLI version is testpilot 0.1.0. Installation and module fingerprints already passed; no product/reinstallation change.")
env={k:v for k,v in os.environ.items() if k!="PYTHONPATH"}
env.update(PYTHONDONTWRITEBYTECODE="1",TMPDIR=str(ROOT/"tmp"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def version(name):
 try:return importlib.metadata.version(name)
 except importlib.metadata.PackageNotFoundError:return None
def run(name,args,timeout=300):
 with (ROOT/(name+".stdout")).open("xb") as out,(ROOT/(name+".stderr")).open("xb") as err:
  result=subprocess.run(args,cwd=ROOT,env=env,stdout=out,stderr=err,stdin=subprocess.DEVNULL,timeout=timeout)
 receipt["commands"].append({"name":name,"args":[str(x) for x in args],"exit_code":result.returncode})
 if result.returncode:raise RuntimeError(name+" failed; inspect saved stdout/stderr")
 return (ROOT/(name+".stdout")).read_text()
try:
 assert sha(ROOT/"testpilot-0.1.0-py3-none-any.whl")==payload["wheel_sha256"]
 modules={x["path"]:x["sha256"] for x in payload["provenance"]["files"] if x["path"].startswith("testpilot/") and x["path"].endswith(".py")}
 assert {name:sha(purelib/name) for name in modules}==modules==prior["installed_module_sha256"]
 console=run("console-version",[str(ENV/"bin/testpilot"),"--version"])
 assert console.strip()=="testpilot 0.1.0"
 receipt["module_entry_version"]=(ROOT/"version.stdout").read_text().strip();receipt["console_entry_version"]=console.strip()
 run("installed-consumer",[str(PY),"-I","-B",str(ROOT/"receive_installed_toolkit.py"),"--source",str(purelib),"--out",str(ROOT/"course-v1")])
 course=json.loads((ROOT/"course-v1/receiving.json").read_text())
 assert course["status"]=="ACCEPT" and course["composed_source_sha256"]==modules
 assert course["recheck_model_calls"]==0 and course["repair_rounds_used"]==1
 assert {name:sha(purelib/name) for name in modules}==modules
 baseline={"pytest":"9.0.2","coverage":None,"pip":None,"testpilot":None}
 assert {name:version(name) for name in baseline}==baseline
 receipt["base_distributions_preserved"]=baseline
 receipt["consumer_receipt"]="course-v1/receiving.json"
 receipt["status"]="qualified_isolated_native_install"
 receipt["limits"]=["New owned review installation only; no existing project/global package mutation.","Existing system pytest is reused read-only; not an independently resolved clean dependency environment.","No coverage, live provider, GitHub Actions, Windows or hardware claim."]
except BaseException as exc:
 receipt["status"]="failed";receipt["error"]=type(exc).__name__+": "+str(exc)
 raise
finally:
 receipt["completed_utc"]=datetime.now(timezone.utc).isoformat()
 (ROOT/"native_receiving-v2.json").write_text(json.dumps(receipt,indent=2))
 print(json.dumps(receipt,indent=2),flush=True)
