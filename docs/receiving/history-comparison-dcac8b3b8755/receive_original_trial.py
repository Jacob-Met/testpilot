"""Receive two exact fictional generation reports through the adopted history CLI."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'testpilot125-current-integration/course/source'
BASE=ROOT.parent/'testpilot125-receiving/candidate-v3-export'
def ident(p):
 b=p.read_bytes();s=p.stat();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'mode':str(s.st_mode),'mtime_ns':str(s.st_mtime_ns),'inode':str(s.st_ino)}
def inventory(root):return {p.relative_to(root).as_posix():ident(p) for p in sorted(root.rglob('*')) if p.is_file()}
assert sys.version_info[:3]==(3,12,14)
assert ident(SOURCE/'testpilot/__main__.py')['git_blob']=='fffa528c6e17460e96d76112d41eba4da1184eaa'
assert ident(SOURCE/'testpilot/history.py')['git_blob']=='b32f19b80241b2744c27991ab60aa500e41c19b9'
assert ident(SOURCE/'testpilot/compare_html.py')['git_blob']=='0fd6c65058fd847342633a28fe6c8c8157b8cfc5'
course=ROOT/'course';course.mkdir();saved=course/'saved-runs';saved.mkdir()
for role in ('before','after'):
 dest=saved/role;dest.mkdir();(dest/'report.json').write_bytes((BASE/(role+'-download.json')).read_bytes())
watched=[Path(__file__).resolve(),BASE/'before-download.json',BASE/'after-download.json']
r={'schema':'hamon.testpilot-discovery-comparison-example/1','scope':'One actual history CLI over two exact fictional downloaded generation inputs; no browser, comparison generation, historical test or model replay.','started':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'passed':False,'source_before':inventory(SOURCE),'inputs_before':inventory(saved),'witness_before':{str(p):ident(p) for p in watched}}
try:
 argv=[sys.executable,'-B','-m','testpilot','history','--root',str(saved),'--kind','generation','--max-depth','1','--json']
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1');env.pop('PYTHONPATH',None)
 child=subprocess.Popen(argv,cwd=SOURCE,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 try:out,err=child.communicate(timeout=30)
 except subprocess.TimeoutExpired:child.kill();out,err=child.communicate();raise
 (course/'history.stdout.json').write_bytes(out);(course/'history.stderr').write_bytes(err)
 r['child']={'argv':argv,'pid':child.pid,'exit':child.returncode};assert child.returncode==0 and err==b''
 result=json.loads(out);assert result['complete'] and result['problems']==[]
 expected={role+'/report.json':ident(saved/role/'report.json')['sha256'] for role in ('before','after')}
 assert {x['path']:x['sha256'] for x in result['runs']}==expected
 assert all(x['kind']=='generation' for x in result['runs']) and result['counts']['matched']==2
 r['result']={'paths_and_sha256':expected,'matched':2,'complete':True};r['passed']=True
except Exception as e:r['error']=type(e).__name__+': '+str(e)
finally:
 r['source_after']=inventory(SOURCE);r['inputs_after']=inventory(saved);r['witness_after']={str(p):ident(p) for p in watched}
 for key in ('source','inputs','witness'):r[key+'_preserved']=r[key+'_before']==r[key+'_after'];r['passed']=r['passed'] and r[key+'_preserved']
 r['finished']=datetime.datetime.now(datetime.timezone.utc).isoformat();(course/'receiving.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({'passed':r['passed'],'child':r.get('child'),'result':r.get('result'),'error':r.get('error'),'receipt':ident(course/'receiving.json')}))
raise SystemExit(0 if r['passed'] else 1)
