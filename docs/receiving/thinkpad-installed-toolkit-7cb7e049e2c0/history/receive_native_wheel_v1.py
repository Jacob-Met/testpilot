"""Receive the reviewed TestPilot wheel on the verified ThinkPad without downloads."""
from datetime import datetime,timezone
import base64,hashlib,importlib.metadata,io,json,os,subprocess,sys,sysconfig,venv,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
payload=json.loads((ROOT/"native_payload_v1.json").read_text())
ENV=ROOT/"venv"
if ENV.exists():raise RuntimeError("venv already exists; inspect prior process before continuing")
PY=ENV/"bin/python"
receipt={"status":"started","owner":"team-7cb7e049e2c0/runtime-consumer","source_commit":payload["provenance"]["source_commit"],"wheel_sha256":payload["wheel_sha256"],"base_python":sys.executable,"base_version":sys.version,"started_utc":datetime.now(timezone.utc).isoformat(),"dependency_mode":"New venv with system-site-packages; existing pytest9.0.2 read-only, no downloads","commands":[]}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def version(name):
 try:return importlib.metadata.version(name)
 except importlib.metadata.PackageNotFoundError:return None
original={name:version(name) for name in ["pytest","coverage","pip","testpilot"]}
env=dict(os.environ);env.pop("PYTHONPATH",None);env.update(PYTHONDONTWRITEBYTECODE="1",PIP_NO_INDEX="1",PIP_DISABLE_PIP_VERSION_CHECK="1",PIP_REQUIRE_VIRTUALENV="1",TMPDIR=str(ROOT/"tmp"))
(ROOT/"tmp").mkdir()
def run(name,args,timeout=300):
 with (ROOT/(name+".stdout")).open("xb") as output,(ROOT/(name+".stderr")).open("xb") as error:
  r=subprocess.run(args,cwd=ROOT,env=env,stdout=output,stderr=error,stdin=subprocess.DEVNULL,timeout=timeout)
 receipt["commands"].append({"name":name,"args":[str(a) for a in args],"exit_code":r.returncode})
 if r.returncode:raise RuntimeError(name+" failed; inspect its stdout/stderr")
 return (ROOT/(name+".stdout")).read_text()
try:
 wheel=base64.b64decode(payload["wheel_base64"]);assert len(wheel)==78834 and hashlib.sha256(wheel).hexdigest()=="cdb743f38fc17fd4caee4f3d0d98761cf8495f8992e2cbb5703444674578f54d"
 with zipfile.ZipFile(io.BytesIO(wheel)) as z:
  assert len(z.namelist())==23
  modules={x["path"]:x["sha256"] for x in payload["provenance"]["files"] if x["path"].startswith("testpilot/") and x["path"].endswith(".py")}
  assert len(modules)==16
  for name,expected in modules.items():assert hashlib.sha256(z.read(name)).hexdigest()==expected
 wheel_path=ROOT/"testpilot-0.1.0-py3-none-any.whl";wheel_path.write_bytes(wheel)
 (ROOT/"receive_installed_toolkit.py").write_text(payload["receiver"])
 (ROOT/"SOURCE_PROVENANCE.json").write_text(json.dumps(payload["provenance"],indent=2))
 (ROOT/"REVIEW_BUILD_README.md").write_text(payload["readme"])
 venv.EnvBuilder(system_site_packages=True,with_pip=True,clear=False).create(ENV)
 info=json.loads(run("environment",[str(PY),"-I","-B","-c","import sys,sysconfig,json,pytest; print(json.dumps({'executable':sys.executable,'prefix':sys.prefix,'purelib':sysconfig.get_path('purelib'),'pytest_version':pytest.__version__,'pytest_file':pytest.__file__}))"]))
 assert Path(info["prefix"]).resolve()==ENV.resolve()
 purelib=Path(info["purelib"]);assert purelib.is_relative_to(ENV)
 assert info["pytest_version"]=="9.0.2"
 receipt["environment"]=info
 run("install",[str(PY),"-I","-B","-m","pip","install","--no-index","--no-deps","--no-compile",str(wheel_path)])
 receipt["installed_module_sha256"]={name:digest(purelib/name) for name in modules}
 assert receipt["installed_module_sha256"]==modules
 stdout=run("version",[str(PY),"-I","-B","-m","testpilot","--version"])
 assert stdout.strip()=="0.1.0",stdout
 console=run("console-version",[str(ENV/"bin/testpilot"),"--version"])
 assert console.strip()=="0.1.0",console
 receipt["module_entry_version"]=stdout.strip();receipt["console_entry_version"]=console.strip()
 run("installed-consumer",[str(PY),"-I","-B",str(ROOT/"receive_installed_toolkit.py"),"--source",str(purelib),"--out",str(ROOT/"course-v1")])
 course=json.loads((ROOT/"course-v1/receiving.json").read_text())
 assert course["status"]=="ACCEPT" and course["composed_source_sha256"]==modules
 assert course["recheck_model_calls"]==0 and course["repair_rounds_used"]==1
 assert {name:digest(purelib/name) for name in modules}==modules
 assert original=={name:version(name) for name in original}
 receipt["base_distributions_preserved"]=original
 receipt["consumer_receipt"]="course-v1/receiving.json"
 receipt["status"]="qualified_isolated_native_install"
 receipt["limits"]=["Isolated review install only; no existing project or global environment changed.","Uses existing system pytest, not an independently resolved clean dependency environment.","No coverage package, live model provider, GitHub Actions, Windows or hardware claim."]
except BaseException as exc:
 receipt["status"]="failed";receipt["error"]=type(exc).__name__+": "+str(exc)
 raise
finally:
 receipt["completed_utc"]=datetime.now(timezone.utc).isoformat()
 (ROOT/"native_receiving.json").write_text(json.dumps(receipt,indent=2))
 print(json.dumps(receipt,indent=2),flush=True)
