"""Qualify exact incoming compare-console composition with the new recheck writer."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
source=ROOT/"composition";shutil.copytree(ROOT/"candidate",source)
packet=json.loads((ROOT/"incoming-current.json").read_text())
for item in packet:
 raw=item["content"].encode()
 if hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()!=item["sha"]:raise RuntimeError("incoming blob mismatch")
 (source/item["path"]).write_bytes(raw)
def snapshot():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob("*") if p.is_file()}
before=snapshot()
env={**os.environ,"TMPDIR":str(ROOT/"tmp"),"PYTHONDONTWRITEBYTECODE":"1","PYTEST_DISABLE_PLUGIN_AUTOLOAD":"1","PYTHONPATH":str(source)}
cmd=[sys.executable,"-B","-m","pytest","-q","-p","no:cacheprovider","tests/test_compare_console.py","tests/test_recheck_html.py::test_actual_html_staging_failure_is_retryable_after_delivery_error"]
began=time.monotonic();p=subprocess.run(cmd,cwd=source,env=env,capture_output=True,text=True,timeout=120)
after=snapshot()
receipt={"scope":"incoming current-main comparison console boundary plus actual recheck staging-failure and explicit retry consumer; no broader rerun","main_commit":"d2596c1a4be11072344c4ea98752cce789865ec4","recovery_commit":"6f4c1cf4ed1f26dd9ceff18a4f8c6be3322cfe85","pid":os.getpid(),"python":sys.version,"incoming":[{"path":x["path"],"git_blob":x["sha"]} for x in packet],"command":cmd,"cwd":str(source),"returncode":p.returncode,"duration_s":time.monotonic()-began,"stdout":p.stdout,"stderr":p.stderr,"source_before":before,"source_after":after,"source_unchanged":before==after}
(ROOT/"composition-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt,indent=2),flush=True)
if p.returncode or before!=after:raise SystemExit(1)
