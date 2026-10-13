import hashlib,json,pathlib,platform,getpass,os,sys,subprocess,importlib.metadata,shutil
root=pathlib.Path(r"D:\hamon-dcac8b3b8755-testpilot-failure-index-v1")
pins=[{"path":"criteria.json","bytes":5482,"git_blob":"3a53360db280b992e5827eda88205840f3daf8ac"},{"path":"intake-original.json","bytes":222285,"git_blob":"a5ebaf44c9ad904d4a13ee498feb0e5177c485f2"},{"path":"receive_browser_v3.py","bytes":13902,"git_blob":"3206962ae468a1d240d0057012e4eee1cc74953d"}]
def identity(path):
 b=path.read_bytes();s=path.stat()
 return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest(),"mode":str(s.st_mode),"mtime_ns":str(s.st_mtime_ns),"inode":str(s.st_ino)}
assert os.name=="nt" and getpass.getuser()=="Veria" and platform.node()=="MSI"
assert sys.version_info[:3]==(3,11,9)
for f in pins:
 actual=identity(root/f["path"])
 assert actual["bytes"]==f["bytes"] and actual["git_blob"]==f["git_blob"],(f,actual)
assert not (root/"original-course-v3").exists()
assert identity(root/"original-course"/"receiving.json")["git_blob"]=="c7d91335b2ec8a0330722870998a31c55c5440d9"
assert identity(root/"original-course-v2"/"receiving.json")["git_blob"]=="8c55b6b2998f4050dddd301cbcf65f4fa018ed6c"
assert shutil.disk_usage(root).free>512*1024*1024
assert pathlib.Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe").is_file()
print(json.dumps({"admitted":True,"user":getpass.getuser(),"host":platform.node(),"python":sys.version,"playwright":importlib.metadata.version("playwright"),"pins":pins}),flush=True)
temp=root/"owned-temp-v3";temp.mkdir(exist_ok=False)
env=os.environ.copy();env["TEMP"]=str(temp);env["TMP"]=str(temp);env["PYTHONDONTWRITEBYTECODE"]="1"
argv=[sys.executable,"-I","-B",str(root/"receive_browser_v3.py"),"original"]
p=subprocess.Popen(argv,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
out,err=p.communicate()
(root/"original-v3.stdout").write_bytes(out);(root/"original-v3.stderr").write_bytes(err)
record={"argv":argv,"pid":p.pid,"exit":p.returncode,"stdout":out.decode("utf-8"),"stderr":err.decode("utf-8")}
with (root/"original-v3-launch.json").open("x",encoding="utf-8",newline="\n") as f:json.dump(record,f,indent=2);f.write("\n")
print(json.dumps(record),flush=True)
raise SystemExit(p.returncode)
