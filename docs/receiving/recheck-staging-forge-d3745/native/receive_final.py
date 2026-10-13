"""Qualify the intentional maintained-test policy update without changing source."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
source=ROOT/"candidate"
def snapshot():
 return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob("*") if p.is_file()}
before=snapshot()
if before["testpilot/recheck.py"]!="1b7d31f49cede49c45fe1fb0613b6e55fac292a7dece9b2645d1b55b141d95f6":raise RuntimeError("writer changed")
if before["tests/test_recheck_html.py"]!="612564571dc0a63d7666bdee4feb07c22bf081585000567d3e70a44327b142d9":raise RuntimeError("test correction changed")
env={**os.environ,"TMPDIR":str(ROOT/"tmp"),"PYTHONDONTWRITEBYTECODE":"1","PYTEST_DISABLE_PLUGIN_AUTOLOAD":"1","PYTHONPATH":str(source)}
cmd=[sys.executable,"-B","-m","pytest","-q","-p","no:cacheprovider","tests/test_recheck.py","tests/test_recheck_html.py","tests/test_recheck_output_staging.py"]
began=time.monotonic();p=subprocess.run(cmd,cwd=source,env=env,capture_output=True,text=True,timeout=120)
after=snapshot()
receipt={"scope":"final bounded recheck/html/staging test receiving after explicit legacy assertion update; original receipt preserved","pid":os.getpid(),"python":sys.version,"command":cmd,"cwd":str(source),"returncode":p.returncode,"duration_s":time.monotonic()-began,"stdout":p.stdout,"stderr":p.stderr,"source_before":before,"source_after":after,"source_unchanged":before==after}
(ROOT/"final-native-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt,indent=2),flush=True)
if p.returncode or before!=after:raise SystemExit(1)
