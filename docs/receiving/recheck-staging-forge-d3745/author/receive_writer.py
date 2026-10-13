"""Receive actual recheck report writer with a child-only file-size limit."""
from pathlib import Path
import errno,hashlib,json,os,subprocess,sys
ROOT=Path('/dev/shm/forge-d3745/testpilot-source')
sys.path.insert(0,str(ROOT))
from testpilot.recheck import RecheckError,write_recheck_outputs
from testpilot.sandbox import SandboxResult,CaseResult
dest=Path(sys.argv[1]);dest.mkdir(parents=True,exist_ok=False)
repo=dest/'project';repo.mkdir()
(repo/'keep.txt').write_text('Original project content.\n')
test='def test_retained():\n    assert True\n'
result={
 'schema':'testpilot.recheck/1','status':'passed','ok':True,'repo':str(repo),
 'python':sys.executable,'started_at':'2026-01-01T00:00:00+00:00','finished_at':'2026-01-01T00:00:01+00:00',
 'source_report':{'path':'authored-original.json','sha256':'a'*64,'recorded_status':'failed'},
 'test_files':{'tests/test_retained.py':test},
 'retained_tests':[{'path':'tests/test_retained.py','bytes':len(test),'sha256':hashlib.sha256(test.encode()).hexdigest(),'placement':'temporary'}],
 'final':SandboxResult(0,False,0.1,10,'Authored writer fixture; no execution claim.',[CaseResult('tests/test_retained.py::test_retained','passed',generated_file='tests/test_retained.py')],generated_files=['tests/test_retained.py'],junit_available=True).to_dict(),
 'model_calls':0,'scope':'Authored writer fixture only; no pytest or provider executed.',
}
request=dest/'request.json';request.write_text(json.dumps(result))
unlimited=write_recheck_outputs(result,dest/'unlimited')
before={k:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for k,p in unlimited.items()}
child="""import errno,json,resource,signal,sys
from pathlib import Path
from testpilot.recheck import write_recheck_outputs
signal.signal(signal.SIGXFSZ,signal.SIG_IGN)
resource.setrlimit(resource.RLIMIT_FSIZE,(4096,4096))
try:write_recheck_outputs(json.loads(Path(sys.argv[1]).read_text()),sys.argv[2])
except OSError as exc:
 print(json.dumps({'type':type(exc).__name__,'errno':exc.errno,'filename':exc.filename}))
 raise SystemExit(72)
raise SystemExit(0)
"""
out=dest/'retry-target'
process=subprocess.run([sys.executable,'-B','-c',child,str(request),str(out)],capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(ROOT),'PYTHONDONTWRITEBYTECODE':'1'})
if process.returncode!=72 or json.loads(process.stdout)['errno']!=errno.EFBIG:raise RuntimeError((process.returncode,process.stdout,process.stderr))
partial={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in out.iterdir()} if out.exists() else {}
try:
 retry=write_recheck_outputs(result,out)
 retried={'status':'succeeded','files':sorted(p.name for p in retry.values())}
except RecheckError as exc:
 retried={'status':'refused','error':str(exc)}
receipt={'scope':result['scope'],'python':sys.version,'source_sha256':hashlib.sha256((ROOT/'testpilot/recheck.py').read_bytes()).hexdigest(),'unlimited_artifacts':before,'limited':{'returncode':process.returncode,'stdout':process.stdout,'stderr':process.stderr,'final_directory_exists':bool(partial),'artifacts':partial},'explicit_unlimited_retry':retried,'project_preserved':(repo/'keep.txt').read_text()=='Original project content.\n','remaining_paths':sorted(p.name for p in dest.iterdir())}
(dest/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
