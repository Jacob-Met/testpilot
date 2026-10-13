"""Run bounded baseline/candidate receiving in an exclusive native stage."""
from pathlib import Path
import hashlib,json,os,pwd,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
packet=json.loads((ROOT/"incoming.json").read_text())
if pwd.getpwuid(os.getuid()).pw_name!="jacob":raise RuntimeError("unexpected native user")
def sha(data):return hashlib.sha256(data).hexdigest()
def git(data):return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
base=ROOT/"baseline";base.mkdir()
pins=[]
for item in packet["originals"]:
    data=item["content"].encode("utf-8")
    if git(data)!=item["sha"]:raise RuntimeError("incoming Git blob mismatch "+item["path"])
    p=base/item["path"];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    pins.append({"path":item["path"],"git_blob":item["sha"],"sha256":sha(data)})
candidate=ROOT/"candidate";shutil.copytree(base,candidate)
for key,expected in (("candidate","1b7d31f49cede49c45fe1fb0613b6e55fac292a7dece9b2645d1b55b141d95f6"),("new_test","aeb39a670ed23f9cb4d31196887022118f94fd46aa51e497f9c7c981772c1cac")):
    item=packet[key];raw=item["content"].encode()
    if sha(raw)!=expected:raise RuntimeError("candidate changed")
    (candidate/item["path"]).write_bytes(raw)
# Identical new tests are also run against the unchanged original writer.
(base/packet["new_test"]["path"]).write_text(packet["new_test"]["content"])
def snapshot(root):
    return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob("*") if p.is_file()}
before={"baseline":snapshot(base),"candidate":snapshot(candidate)}
tmp=ROOT/"tmp";tmp.mkdir()
env={**os.environ,"TMPDIR":str(tmp),"PYTHONDONTWRITEBYTECODE":"1","PYTEST_DISABLE_PLUGIN_AUTOLOAD":"1"}
receipt={"scope":"native ThinkPad local authored projects and exact retained tests; no model/provider or installed project change","pid":os.getpid(),"user":pwd.getpwuid(os.getuid()).pw_name,"python":sys.version,"base_commit":packet["base_commit"],"original_pins":pins,"source_before":before,"courses":[]}
courses=[
 ("baseline_inherited",base,["-m","pytest","-q","-p","no:cacheprovider","tests/test_recheck.py","tests/test_recheck_html.py"]),
 ("baseline_focused",base,["tests/test_recheck_output_staging.py"]),
 ("candidate_inherited",candidate,["-m","pytest","-q","-p","no:cacheprovider","tests/test_recheck.py","tests/test_recheck_html.py"]),
 ("candidate_focused",candidate,["tests/test_recheck_output_staging.py"]),
 ("candidate_optimized",candidate,["-O","tests/test_recheck_output_staging.py"]),
]
for name,source,args in courses:
    course_env={**env,"PYTHONPATH":str(source)}
    began=time.monotonic()
    process=subprocess.run([sys.executable,"-B",*args],cwd=source,env=course_env,capture_output=True,text=True,timeout=120)
    (ROOT/(name+".stdout")).write_text(process.stdout)
    (ROOT/(name+".stderr")).write_text(process.stderr)
    entry={"name":name,"command":[sys.executable,"-B",*args],"cwd":str(source),"returncode":process.returncode,"duration_s":time.monotonic()-began,"stdout":process.stdout,"stderr":process.stderr}
    receipt["courses"].append(entry)
    print(json.dumps({"name":name,"returncode":process.returncode,"duration_s":entry["duration_s"]}),flush=True)
after={"baseline":snapshot(base),"candidate":snapshot(candidate)}
receipt["source_after"]=after
receipt["source_unchanged"]=before==after
(ROOT/"native-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
required=all(c["returncode"]==0 for c in receipt["courses"] if c["name"]!="baseline_focused")
print(json.dumps({"done":True,"source_unchanged":receipt["source_unchanged"],"candidate_and_inherited_pass":required,"receipt_sha256":sha((ROOT/"native-receipt.json").read_bytes())}),flush=True)
if not required or before!=after:raise SystemExit(1)
