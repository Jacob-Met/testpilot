import os,sys,json,hashlib,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
root=Path(__file__).resolve().parent
reserve=805306368; own_limit=16777216
def used(): return sum(p.stat().st_size for p in root.rglob("*") if p.is_file() and not p.is_symlink())
def guard():
 v=os.statvfs(root);free=v.f_bavail*v.f_frsize
 assert free>=reserve+own_limit,(free,reserve)
 assert used()<own_limit,used()
 return free
def pins():
 out={}
 for variant in ("baseline","candidate"):
  for p in (root/variant).rglob("*"):
   if p.is_file():
    b=p.read_bytes();out[str(p.relative_to(root))]=hashlib.sha256(b).hexdigest()
 return out
before=pins();results=[]
for variant in ("baseline","candidate"):
 free=guard();source=root/variant
 temp=root/(variant+"-work");temp.mkdir()
 env=os.environ.copy();env.update({"PYTHONDONTWRITEBYTECODE":"1","PYTHONPATH":str(source),"TMPDIR":str(temp),"PYTEST_DISABLE_PLUGIN_AUTOLOAD":"1"})
 env.pop("PYTEST_ADDOPTS",None)
 cmd=[sys.executable,"-B","-m","pytest","-q","-p","no:cacheprovider","tests/test_fenced_code_boundaries.py","tests/test_generated_test_preservation.py::test_conflicting_alias_and_canonical_repairs_preserve_previous_tests","--junitxml="+str(root/(variant+"-junit.xml")),"--basetemp="+str(temp/"pytest")]
 r=subprocess.run(cmd,cwd=source,env=env,capture_output=True,text=True,timeout=90)
 (root/(variant+"-stdout.log")).write_text(r.stdout,encoding="utf-8");(root/(variant+"-stderr.log")).write_text(r.stderr,encoding="utf-8")
 suites=ET.parse(root/(variant+"-junit.xml")).getroot()
 rows=[x for x in suites.iter("testsuite")]
 counts={k:sum(int(x.attrib.get(k,0)) for x in rows) for k in ("tests","failures","errors","skipped")}
 result={"variant":variant,"command":cmd,"cwd":str(source),"exit_code":r.returncode,"counts":counts,"free_before":free}
 results.append(result);print(json.dumps(result,sort_keys=True),flush=True)
after=pins();assert before==after
out={"schema":"testpilot-fence-compatibility/1","receiving_head":"c138a7992fa35066d115dee6e8fddef33496b54c","changed_runtime_node":"_FENCE","results":results,"all_source_bytes_unchanged":True,"source_sha256":before,"free_after":guard(),"native_root":str(root),"native_bytes":used(),"scope":"Twelve prior fence controls, two new adjacent-fence orders, and the two actual hosted-failure consumer cases only; not a full suite."}
(root/"native-results.json").write_text(json.dumps(out,sort_keys=True,indent=2)+"\n",encoding="utf-8")
assert results[0]["exit_code"]==1 and results[0]["counts"]=={"tests":16,"failures":4,"errors":0,"skipped":0},results[0]
assert results[1]["exit_code"]==0 and results[1]["counts"]=={"tests":16,"failures":0,"errors":0,"skipped":0},results[1]
print(json.dumps({"accepted":True,"results_file":str(root/"native-results.json"),"all_source_bytes_unchanged":True,"native_bytes":used()},sort_keys=True))
