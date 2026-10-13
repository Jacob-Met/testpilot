import base64,datetime,hashlib,json,os,pathlib,platform,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/"candidate-producer-v1"
OUT.mkdir(exist_ok=False)
def ident(p):
 b=p.read_bytes();s=p.stat();return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"git":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest(),"mode":s.st_mode,"mtime_ns":str(s.st_mtime_ns),"inode":str(s.st_ino)}
def snap(folder):
 return {str(p.relative_to(folder)).replace(os.sep,"/"):ident(p) for p in sorted(folder.rglob("*")) if p.is_file()}
r={"schema":"hamon.testpilot-candidate-render/1","utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"host":platform.node(),"uid":os.getuid(),"python":platform.python_version(),"passed":False,"commands":[]}
try:
 if os.getuid()!=1000 or sys.version_info<(3,12):raise RuntimeError("Unsupported producer identity/runtime")
 sp=ROOT/"candidate-source-packet.json"; fp=ROOT/"fixture-packet-v1.json"
 if ident(sp)["sha256"]!="a37efe9a6b0b21d422c14226cf9460855c509fdebd02b1ddc885b61de1ba73f1":raise RuntimeError("Source packet mismatch")
 if ident(fp)["git"]!="4812eb0446a0f1d9d53dfbe119825f492db9c96e":raise RuntimeError("Fixture packet mismatch")
 packet=json.loads(sp.read_bytes()); fixtures=json.loads(fp.read_bytes())
 source=OUT/"source"; inputs=OUT/"fixtures"; pages=OUT/"pages"
 for folder in (source,inputs,pages):folder.mkdir()
 for item in packet["files"]:
  rel=pathlib.PurePosixPath(item["path"])
  if rel.is_absolute() or ".." in rel.parts:raise RuntimeError("Unsafe packet path")
  data=item["content"].encode("utf-8")
  if len(data)!=item["bytes"] or hashlib.sha256(data).hexdigest()!=item["sha256"] or hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()!=item["git_blob"]:raise RuntimeError("Source member mismatch")
  path=source.joinpath(*rel.parts);path.parent.mkdir(parents=True,exist_ok=True)
  with path.open("xb") as f:f.write(data)
  path.chmod(int(item["mode"],8)&0o777)
 for item in fixtures["files"]:
  with (inputs/item["path"]).open("xb") as f:f.write(item["content"].encode("utf-8"))
 (OUT/"criteria.json").write_bytes((json.dumps(fixtures["criteria"],ensure_ascii=False,indent=2)+"\n").encode("utf-8"))
 r["source_before"]=snap(source);r["fixtures_before"]=snap(inputs);r["packet_before"]={str(p.name):ident(p) for p in (sp,fp,ROOT/"produce_candidate.py")}
 for page in fixtures["criteria"]["pages"]:
  destination=pages/(page["name"]+".html")
  args=[sys.executable,"-B","-m","testpilot","compare","--before",str(inputs/page["before"]),"--after",str(inputs/page["after"]),"--out",str(destination)]
  proc=subprocess.Popen(args,cwd=source,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  try:stdout,stderr=proc.communicate(timeout=45)
  except subprocess.TimeoutExpired:
   proc.kill();proc.communicate();raise
  (OUT/(page["name"]+".stdout.txt")).write_bytes(stdout);(OUT/(page["name"]+".stderr.txt")).write_bytes(stderr)
  r["commands"].append({"name":page["name"],"args":args,"pid":proc.pid,"returncode":proc.returncode,"stdout":ident(OUT/(page["name"]+".stdout.txt")),"stderr":ident(OUT/(page["name"]+".stderr.txt"))})
  if proc.returncode!=0 or not destination.is_file():raise RuntimeError("Renderer failed")
 r["pages"]=snap(pages)
 r["source_after"]=snap(source);r["fixtures_after"]=snap(inputs);r["packet_after"]={str(p.name):ident(p) for p in (sp,fp,ROOT/"produce_candidate.py")}
 if r["source_before"]!=r["source_after"] or r["fixtures_before"]!=r["fixtures_after"] or r["packet_before"]!=r["packet_after"]:raise RuntimeError("Conservation failure")
 r["passed"]=True
except BaseException as e:r["error"]=type(e).__name__+": "+str(e)
finally:
 raw=(json.dumps(r,ensure_ascii=False,indent=2)+"\n").encode("utf-8");(OUT/"receiving.json").write_bytes(raw)
 print(json.dumps({"passed":r["passed"],"commands":r["commands"],"receipt":ident(OUT/"receiving.json"),"error":r.get("error")}))
if r["passed"]:
 members=[OUT/"criteria.json",OUT/"receiving.json",*sorted((OUT/"fixtures").glob("*.json")),*sorted((OUT/"pages").glob("*.html"))]
 transfer={"schema":"hamon.testpilot-browser-intake/1","candidate_source":packet["commit"],"source_packet_git":"632f16c2e40ee934f6af9593f9808ba43c768b2d","fixture_packet_git":"4812eb0446a0f1d9d53dfbe119825f492db9c96e","files":[]}
 for p in members:transfer["files"].append({"path":p.relative_to(OUT).as_posix(),"identity":ident(p),"base64":base64.b64encode(p.read_bytes()).decode("ascii")})
 (OUT/"browser-intake-packet.json").write_bytes((json.dumps(transfer,ensure_ascii=False,indent=2)+"\n").encode("utf-8"))
 print(json.dumps({"browser_packet":ident(OUT/"browser-intake-packet.json")}))
raise SystemExit(0 if r["passed"] else 1)
