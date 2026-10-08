import hashlib, json, os, pathlib, subprocess, time
ROOT=pathlib.Path('/dev/shm/testpilot-490f-compare-latest')
OLD=pathlib.Path('/dev/shm/testpilot-490f-compare')
PYTHON='/home/jacob/hamon-universal-e3a41d2b3368-testpilot-main-9f01/complete-tooling-receiving/venv-pytest9-complete/bin/python'
ENV=dict(os.environ,PYTHONPATH=str(ROOT/'candidate'),TMPDIR='/dev/shm/tp490f-tmp',PYTHONDONTWRITEBYTECODE='1',TESTPILOT_BACKEND='receiving-must-not-call-a-provider')
proof={'baseCommit':'63174afd8e63a0ea562cf188b7d971522f017a30','commands':[],'checks':[]}
def run(args,expected):
    cmd=[PYTHON,'-B',*args]
    t=time.monotonic()
    p=subprocess.run(cmd,cwd=ROOT/'candidate',env=ENV,capture_output=True,text=True,timeout=120)
    item={'command':cmd,'returncode':p.returncode,'seconds':time.monotonic()-t,'stdout':p.stdout,'stderr':p.stderr}
    proof['commands'].append(item)
    assert p.returncode==expected,item
    return p
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot(p):return {str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def check(name):proof['checks'].append({'name':name,'passed':True})
try:
    run(['-m','pytest','-q','-p','no:cacheprovider','tests/test_compare_cli.py','tests/test_recheck.py::test_cli_skips_generation_and_recheck_output_is_reusable','tests/test_recheck.py::test_output_admission_precedes_execution'],0)
    check('New comparison CLI and inherited real reusable-recheck/output-admission routes coexist')
    before=OLD/'evidence/baseline/before/report.json';after=OLD/'evidence/baseline/after/report.json'
    repo=OLD/'fixtures/after'
    before_hash,after_hash=sha(before),sha(after);source_snapshot=snapshot(repo)
    output=ROOT/'evidence/native-generation-pair.html'
    run(['-m','testpilot','compare','--before',str(before),'--after',str(after),'--out',str(output)],0)
    assert output.read_bytes()==(OLD/'evidence/candidate/native-pair-fixed.html').read_bytes()
    check('Current CLI generation-report comparison equals exact frozen 48,157-byte HTML')
    rechecked=ROOT/'evidence/current-recheck'
    run(['-m','testpilot','recheck','--repo',str(repo),'--report',str(before),'--python',PYTHON,'--timeout','10','--out',str(rechecked)],0)
    result=json.loads((rechecked/'recheck.json').read_bytes())
    assert result['schema']=='testpilot.recheck/1'
    assert result['status']=='passed' and result['model_calls']==0
    assert result['final']['passed']==6 and result['final']['generated']['passed']==4
    assert result['test_files']==json.loads(before.read_bytes())['test_files']
    assert result['source_report']['sha256']==before_hash
    check('Actual recheck retains exact tests, six suite/four generated passes, zero model calls and source-report identity')
    recheck_hash=sha(rechecked/'recheck.json')
    refused=ROOT/'evidence/recheck-comparison-must-not-exist.html'
    p=run(['-m','testpilot','compare','--before',str(before),'--after',str(rechecked/'recheck.json'),'--out',str(refused)],2)
    assert 'missing fields' in p.stderr and not refused.exists()
    assert sha(rechecked/'recheck.json')==recheck_hash
    check('Distinct recheck/1 schema is refused without synthesizing historical source, coverage or usage')
    p=run(['-m','testpilot','--help'],0)
    assert '{run,targets,recheck,compare}' in p.stdout
    p=run(['-m','testpilot','targets','--repo',str(repo),'--diff',str(OLD/'baseline/eval/cases/calc_clamp/change.diff'),'--json'],0)
    selected=json.loads(p.stdout)
    assert len(selected['changed_functions'])==1 and selected['changed_functions'][0]['qualname']=='clamp'
    check('All four parser commands remain present and raw-diff target preview still returns the maintained function')
    assert sha(before)==before_hash and sha(after)==after_hash and snapshot(repo)==source_snapshot
    check('Original native reports and fixed source project remain byte-identical')
    proof['outputs']=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in [output,rechecked/'recheck.json',rechecked/'recheck.md']]
    proof['passed']=True
except BaseException as exc:
    proof['passed']=False;proof['error']=str(exc);raise
finally:
    path=ROOT/'evidence/coexistence-gate.json';path.write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps({'passed':proof.get('passed'),'checks':proof['checks'],'commands':len(proof['commands']),'receipt':str(path),'sha256':sha(path),'error':proof.get('error')}))
