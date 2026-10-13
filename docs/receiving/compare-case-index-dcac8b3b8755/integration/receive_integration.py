"""Current-main history/qualified-index integration through one supported ordinary CLI."""
from pathlib import Path
import base64, hashlib, json, os, platform, subprocess, sys

ROOT = Path(__file__).resolve().parent
INTAKE = ROOT.parent / "testpilot125-receiving" / "intake-current-main-integration.json"
EXPECTED_INTAKE = "98096bcdde5b0dad71c6e2a8a23ac16552e3db33"
def identity(p):
    b=p.read_bytes();st=p.stat()
    return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),
            "git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest(),
            "mode":str(st.st_mode),"mtime_ns":str(st.st_mtime_ns),"inode":str(st.st_ino)}
def inventory(p):
    return {q.relative_to(p).as_posix():identity(q) if q.is_file() else {"directory":True}
            for q in sorted(p.rglob("*"))}
out=ROOT/"course";out.mkdir()
source=out/"source";source.mkdir();fixtures=out/"fixtures";fixtures.mkdir()
r={"schema":"testpilot.case-index-current-main-integration/1","python":sys.version,
   "executable":sys.executable,"platform":platform.platform(),"pid":os.getpid(),
   "passed":False,"checks":[],"scope":"One supported current-main CLI composition. No original, browser, pytest or history command replay. The composed compare output must equal previously browser-received candidate HTML bytes."}
def check(name,actual,expected):
    passed=actual==expected;r["checks"].append({"name":name,"actual":actual,"expected":expected,"passed":passed})
    if not passed:raise RuntimeError(name)
witness={str(p):identity(p) for p in (INTAKE,Path(__file__).resolve())}
witness[str(ROOT.parent/"testpilot125-receiving"/"candidate-v3-export"/"comparison.html")]=identity(ROOT.parent/"testpilot125-receiving"/"candidate-v3-export"/"comparison.html")
r["witness_before"]=witness
try:
    check("supported local Python",list(sys.version_info[:3]),[3,12,14])
    check("exact independent candidate intake",identity(INTAKE)["git_blob"],EXPECTED_INTAKE)
    p=json.loads(INTAKE.read_bytes());check("candidate phase",p["phase"],"integration")
    check("full selected runtime count",len(p["source"]["files"]),16)
    for f in p["source"]["files"]:
        dest=source/f["path"];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(f["content"].encode("utf-8"))
        got=identity(dest);check("source "+f["path"],[got[k] for k in ("bytes","sha256","git_blob")],[f[k] for k in ("bytes","sha256","git_blob")])
    for f in p["fixtures"]:
        dest=fixtures/f["path"];dest.write_bytes(base64.b64decode(f["base64"],validate=True))
        got=identity(dest);check("fixture "+f["path"],[got[k] for k in ("bytes","sha256","git_blob")],[f[k] for k in ("bytes","sha256","git_blob")])
    r["source_before"]=inventory(source);r["fixtures_before"]=inventory(fixtures)
    argv=[sys.executable,"-B","-m","testpilot","compare","--before",str(fixtures/"before.json"),"--after",str(fixtures/"after.json"),"--out",str(out/"comparison.html")]
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1")
    env.pop("PYTHONPATH",None)
    with (out/"producer.stdout").open("xb") as stdout,(out/"producer.stderr").open("xb") as stderr:
        child=subprocess.Popen(argv,cwd=source,env=env,stdout=stdout,stderr=stderr)
        r["child"]={"argv":argv,"cwd":str(source),"pid":child.pid}
        try:r["child"]["returncode"]=child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            child.kill();r["child"]["returncode"]=child.wait(timeout=10);raise
    check("ordinary compare CLI exit",r["child"]["returncode"],0)
    check("ordinary compare CLI stderr",(out/"producer.stderr").read_bytes(),b"")
    r["html"]=identity(out/"comparison.html")
    accepted=ROOT.parent/"testpilot125-receiving"/"candidate-v3-export"/"comparison.html"
    check("composed HTML whole-byte parity",(out/"comparison.html").read_bytes()==accepted.read_bytes(),True)
    r["accepted_html_identity"]=identity(accepted)
    r["passed"]=True
except Exception as e:
    r["error"]=type(e).__name__+": "+str(e)
finally:
    r["source_after"]=inventory(source);r["fixtures_after"]=inventory(fixtures)
    r["witness_after"]={q:identity(Path(q)) for q in witness}
    for label in ("source","fixtures","witness"):
        r[label+"_preserved"]=r.get(label+"_before")==r[label+"_after"]
        r["passed"]=r["passed"] and r[label+"_preserved"]
    r["streams"]={n:identity(out/n) for n in ("producer.stdout","producer.stderr") if (out/n).exists()}
    # JSON represents the empty byte-string check as an explicit empty text value.
    for row in r["checks"]:
        for key in ("actual","expected"):
            if isinstance(row[key],bytes):row[key]=row[key].decode("utf-8")
    (out/"receiving.json").write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"passed":r["passed"],"checks":len(r["checks"]),"child":r.get("child"),"html":r.get("html"),"receipt":identity(out/"receiving.json"),"error":r.get("error")}))
raise SystemExit(0 if r["passed"] else 1)
