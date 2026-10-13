from pathlib import Path
import shutil, subprocess, os, json, hashlib, sys
r=Path('/dev/shm/hamon-1caa-testpilot-wheel')
root=r/'consumer'
root.mkdir()
shutil.copytree(r/'source/eval/cases/calc_clamp',root/'sample')
python=r/'installed-env/bin/python'
def guard(p):
 s=p.stat();return {'bytes':s.st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mtime_ns':s.st_mtime_ns,'mode':s.st_mode,'inode':s.st_ino}
files=[p for p in (root/'sample').rglob('*') if p.is_file()]
before={str(p.relative_to(root)):guard(p) for p in files}
installed=r/'installed-env/lib/python3.12/site-packages/testpilot'
for p in (r/'source/testpilot').glob('*.py'):
 if p.read_bytes()!=(installed/p.name).read_bytes():raise RuntimeError('installed mismatch')
env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1';env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1';env['TMPDIR']=str(r/'tmp')
for k in ['PYTHONPATH','TESTPILOT_BACKEND','TESTPILOT_SCRIPT','TESTPILOT_BASE_URL','TESTPILOT_PRICES','TESTPILOT_PLANNER_MODEL','TESTPILOT_EDITOR_MODEL']:
 env.pop(k,None)
runs=[]
commands=[
 ('help',['--help'],0),
 ('targets',['targets','--repo','sample/repo','--diff','sample/change.diff','--json'],0),
 ('scripted',['run','--repo','sample/repo','--diff','sample/change.diff','--backend','scripted','--script','sample/script','--out','result','--no-coverage','--python',str(python)],1)
]
for name,args,expected in commands:
 command=[str(python),'-I','-B','-m','testpilot']+args
 p=subprocess.run(command,cwd=root,env=env,capture_output=True,timeout=35)
 (r/(name+'.stdout.txt')).write_bytes(p.stdout);(r/(name+'.stderr.txt')).write_bytes(p.stderr)
 runs.append({'name':name,'command':command,'exit_code':p.returncode,'stdout':p.stdout.decode(),'stderr':p.stderr.decode()})
 if p.returncode!=expected:
  (r/'consumer-failure.json').write_text(json.dumps(runs,indent=2)+'\n')
  raise RuntimeError(name+' unexpected exit '+str(p.returncode))
report=json.loads((root/'result/report.json').read_text())
if report['status']!='suspected_code_bug':raise RuntimeError('wrong recorded outcome')
after={str(p.relative_to(root)):guard(p) for p in files}
if before!=after:raise RuntimeError('sample changed')
outputs={p.name:guard(p) for p in (root/'result').iterdir() if p.is_file()}
if set(outputs)!={'report.json','report.md','report.html','testpilot.patch'}:raise RuntimeError('outputs incomplete')
receipt={'schema':'testpilot.wheel-scripted-consumer.v1','result':'PASS','source_commit':'d2596c1a4be11072344c4ea98752cce789865ec4','wheel_sha256':hashlib.sha256((r/'wheel/testpilot-0.1.0-py3-none-any.whl').read_bytes()).hexdigest(),'installed14modules_exact':True,'sample_before':before,'sample_after':after,'sample_unchanged':True,'commands':runs,'report_status':report['status'],'recorded_final':report.get('final'),'outputs':outputs,'limits':'Cloud Linux installed wheel outside source with existing read-only pytest dependency provider. No live model/provider, native machine, browser visual or installed-estate adoption. Expected sample exit1 preserves suspected_code_bug and failing tests.'}
dest=r/'consumer-receipt.json';dest.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'result':'PASS','receipt':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'status':report['status'],'outputs':list(outputs),'final':report.get('final')},indent=2))

