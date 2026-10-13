"""Receive the frozen TestPilot wheel through its documented no-network course."""
from pathlib import Path
import hashlib, json, os, socket, subprocess, sys, time
ROOT=Path("/home/jacob/hamon-testpilot-package-1caa1d8e028a")
KIT=ROOT/"kit"
RESULT=ROOT/"independent"
RESULT.mkdir(exist_ok=False)
ENV=ROOT/"testpilot-review"
if ENV.exists(): raise RuntimeError("refuse an existing review environment")
def ident(p):
 b=p.read_bytes();s=p.stat()
 return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"mtime_ns":s.st_mtime_ns,"mode":s.st_mode,"inode":s.st_ino}
before={str(p.relative_to(KIT)):ident(p) for p in KIT.rglob("*") if p.is_file()}
environment=dict(os.environ)
for k in ["PYTHONPATH","NEBIUS_API_KEY","OPENAI_API_KEY","ANTHROPIC_API_KEY","QLOO_API_KEY"]:
 environment.pop(k,None)
environment.update(PYTHONDONTWRITEBYTECODE="1",PYTHONNOUSERSITE="1",PIP_DISABLE_PIP_VERSION_CHECK="1")
receipt={"source_commit":"d2596c1a4be11072344c4ea98752cce789865ec4","source_tree":"3b6d270f655310fa2f98cab9bccffca23ec146cf","kit_sha256":"8b3c856751ae9bd24b74474b68624e38e97d9157429aafc6c9d671676be00a4d","device":"d55b2499-5e82-4805-819a-d0d7ddea1efe","hostname":socket.gethostname(),"uid":os.getuid(),"python":sys.version,"controller_pid":os.getpid(),"scope":"Isolated ordinary installed-wheel qualification; no installed-project adoption, providers or dependency downloads","calls":[],"checks":[],"input_before":before}
def save():
 (RESULT/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
def call(name,arguments,expected=0,timeout=90):
 start=time.monotonic()
 process=subprocess.Popen([str(a) for a in arguments],cwd=KIT,env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 record={"name":name,"pid":process.pid,"command":[str(a) for a in arguments],"expected_exit":expected}
 receipt["calls"].append(record);save()
 try:stdout,stderr=process.communicate(timeout=timeout)
 except subprocess.TimeoutExpired:
  process.kill();stdout,stderr=process.communicate();record["timed_out"]=True
 record.update(exit_code=process.returncode,duration_s=time.monotonic()-start)
 for label,data in [("stdout",stdout),("stderr",stderr)]:
  (RESULT/(name+"."+label)).write_bytes(data)
  record[label]={"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
 save()
 if process.returncode!=expected or record.get("timed_out"):
  raise RuntimeError("unexpected process result: "+name)
 return stdout
try:
 call("venv",[sys.executable,"-B","-m","venv","--system-site-packages",ENV])
 python=ENV/"bin/python"
 call("pytest-version",[python,"-I","-m","pytest","--version"])
 call("install",[python,"-B","-m","pip","install","--no-index","--no-deps",KIT/"testpilot-0.1.0-py3-none-any.whl"])
 code="from pathlib import Path;import hashlib,json,sys,testpilot,pytest; p=Path(testpilot.__file__).parent; print(json.dumps({'python':sys.version,'prefix':sys.prefix,'package':str(p),'pytest':pytest.__version__,'files':{str(f.relative_to(p.parent)):{'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size} for f in p.rglob('*.py')}}))"
 installed=json.loads(call("installed-identity",[python,"-I","-B","-c",code]))
 receipt["installed"]=installed
 if not Path(installed["package"]).is_relative_to(ENV):raise RuntimeError("package is not from isolated environment")
 expected={x["path"]:x for x in json.loads((KIT/"SOURCE_MANIFEST.json").read_text())["files"] if x["path"].startswith("testpilot/") and x["path"].endswith(".py")}
 if set(installed["files"])!=set(expected):raise RuntimeError("installed module set")
 for name,value in installed["files"].items():
  if value["sha256"]!=expected[name]["sha256"] or value["bytes"]!=expected[name]["bytes"]:raise RuntimeError("installed module differs: "+name)
 receipt["checks"].append({"name":"14 exact installed source modules","pass":len(expected)==14})
 call("help",[python,"-I","-B","-m","testpilot","--help"])
 targets=json.loads(call("targets",[python,"-I","-B","-m","testpilot","targets","--repo","sample/repo","--diff","sample/change.diff","--json"]))
 receipt["target_preview"]=targets
 call("scripted",[python,"-I","-B","-m","testpilot","run","--repo","sample/repo","--diff","sample/change.diff","--backend","scripted","--script","sample/script","--out",RESULT/"sample-result","--no-coverage"],expected=1,timeout=120)
 report=json.loads((RESULT/"sample-result/report.json").read_text())
 final=report["final"]
 checks={"suspected_code_bug":report["status"]=="suspected_code_bug","four_generated":report["tests_written"]==4 and final["generated"]["collected"]==4,"three_failed_three_passed":final["failed"]==3 and final["passed"]==3 and final["errors"]==0 and not final["timed_out"],"only_clamp_changed":len(report["changed_functions"])==1 and report["changed_functions"][0]["qualname"]=="clamp","four_outputs":set(p.name for p in (RESULT/"sample-result").iterdir())=={"report.html","report.json","report.md","testpilot.patch"}}
 receipt["checks"].extend({"name":k,"pass":v} for k,v in checks.items())
 receipt["observed"]={"status":report["status"],"tests_written":report["tests_written"],"final":{k:final[k] for k in ["returncode","timed_out","passed","failed","errors","skipped","generated"]}}
 receipt["reports"]={p.name:ident(p) for p in (RESULT/"sample-result").iterdir()}
except Exception as exc:
 receipt["error"]={"type":type(exc).__name__,"message":str(exc)}
finally:
 after={str(p.relative_to(KIT)):ident(p) for p in KIT.rglob("*") if p.is_file()}
 receipt["input_after"]=after
 receipt["checks"].append({"name":"entire kit bytes and metadata unchanged","pass":before==after})
 receipt["pass"]=not receipt.get("error") and all(x["pass"] for x in receipt["checks"])
 save()
 print(json.dumps({"receipt":str(RESULT/"receipt.json"),"pass":receipt["pass"],"checks":receipt["checks"],"error":receipt.get("error"),"calls":[{"name":x["name"],"pid":x["pid"],"exit_code":x.get("exit_code")} for x in receipt["calls"]]}))
sys.exit(0 if receipt["pass"] else 1)
