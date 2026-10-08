"""Independent receiver: raw diff transport must ignore the console codec."""
import base64, hashlib, json, os, pathlib, subprocess, sys, time
ROOT = pathlib.Path("/Users/me/hamon-testpilot-receiving-db371a37f4c8/final")
SOURCE = pathlib.Path('/Users/me/hamon-product-db371a37f4c8')
ORIGINAL = SOURCE / 'original-platform-controls'
CANDIDATE = SOURCE / 'testpilot-diff-transport'
EXPECTED_CLI = '83caf8df097902120a0cfbd6adb897d5b6be7ba2407b0217606e7038599b5a5f'
sha = lambda b: hashlib.sha256(b).hexdigest()
def source_hashes(base):
    return {str(p.relative_to(base)):sha(p.read_bytes()) for p in sorted((base/'testpilot').rglob('*.py'))}
before = {label:source_hashes(base) for label,base in [('original',ORIGINAL),('candidate',CANDIDATE)]}
assert before['candidate']['testpilot/__main__.py'] == EXPECTED_CLI
assert not (ROOT/'receipt.json').exists(), 'Preserve existing independent evidence'
repo = ROOT/'project'
(repo/'tests').mkdir(parents=True, exist_ok=False)
env = {'PATH':os.defpath,'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull,'TMPDIR':str(ROOT)}
commands = []
def run(args, *, extra=None, data=None, cwd=repo):
    result = subprocess.run([str(a) for a in args], cwd=cwd, env={**env,**(extra or {})}, input=data, capture_output=True, timeout=35)
    commands.append({'argv':[str(a) for a in args],'returncode':result.returncode,'stdoutBase64':base64.b64encode(result.stdout).decode(),'stderrBase64':base64.b64encode(result.stderr).decode()})
    return result
def git(*args):
    r=run(['git','-C',repo,*args])
    assert r.returncode==0, r.stderr
    return r.stdout
name = '計測.py'
before_text = "# coding: cp1252\ndef value():\n    return '€', 1\n"
after_text = before_text.replace("'€', 1", "'€', 2")
(repo/name).write_bytes(before_text.encode('cp1252'))
(repo/'tests/test_existing.py').write_text("import importlib\ndef test_existing():\n    assert importlib.import_module('計測').value()[0] == '€'\n",encoding='utf-8')
git('init','-q')
git('config','core.quotePath','false')
git('add','.')
git('-c','user.name=Root Receiving','-c','user.email=receiving@invalid.local','-c','commit.gpgsign=false','commit','-qm','fixture baseline')
(repo/name).write_bytes(after_text.encode('cp1252'))
raw = git('diff','HEAD','--','*.py')
assert name.encode('utf-8') in raw and b'\x80' in raw
try: raw.decode('utf-8')
except UnicodeDecodeError: pass
else: raise AssertionError('Receiver needs a real non-UTF8 hunk')
diff = ROOT/'raw-change.diff';diff.write_bytes(raw)
expected_source = after_text.split('\n',1)[1].rstrip('\n')
fixture_before = {str(p.relative_to(repo)):sha(p.read_bytes()) for p in repo.rglob('*') if p.is_file() and '.git' not in p.parts}
rows=[]
for label,base in [('original',ORIGINAL),('candidate',CANDIDATE)]:
    for route in ['file','stdin']:
        args=[sys.executable,'-B','-m','testpilot','targets','--repo',repo,'--diff','-' if route=='stdin' else diff,'--json']
        r=run(args,extra={'PYTHONPATH':str(base),'PYTHONIOENCODING':'cp1252:strict'},data=raw if route=='stdin' else None)
        result=json.loads(r.stdout) if r.returncode==0 else None
        rows.append({'source':label,'route':route,'code':r.returncode,'targets':result,'stderr':r.stderr.decode('ascii','backslashreplace')})
        if label=='candidate':
            assert r.returncode==0 and r.stderr==b'', rows[-1]
            targets=result['changed_functions']
            assert len(targets)==1 and targets[0]['path']==name and targets[0]['qualname']=='value'
            assert targets[0]['changed_lines']==[3] and targets[0]['source']==expected_source, targets
        elif route=='file':
            assert r.returncode==2 and b'utf-8' in r.stderr, rows[-1]
        else:
            assert r.returncode==0 and result=={'changed_functions':[]}, rows[-1]
script_dir = ROOT/'script';script_dir.mkdir()
(script_dir/'01.txt').write_text('Check the changed tuple contract.\n')
test_text="import importlib\ndef test_generated_value():\n    assert importlib.import_module('計測').value() == ('€', 2)\n"
(script_dir/'02.txt').write_text(chr(96)*3+'python path=tests/test_generated_value.py\n'+test_text+chr(96)*3+'\n',encoding='utf-8')
out=ROOT/'run-output'
r=run([sys.executable,'-B','-m','testpilot','run','--repo',repo,'--diff','-','--backend','scripted','--script',script_dir,'--rounds','0','--python',sys.executable,'--timeout','15','--out',out],extra={'PYTHONPATH':str(CANDIDATE),'PYTHONIOENCODING':'utf-8:strict'},data=raw)
assert r.returncode==0, (r.returncode,r.stdout,r.stderr)
report=json.loads((out/'report.json').read_text())
assert report['status']=='passed' and report['tests_written']==1,report
assert report['final']['generated']=={'collected':1,'passed':1,'failed':0,'error':0,'skipped':0},report['final']
assert report['final']['passed']==2
assert report['test_files']=={'tests/test_generated_value.py':test_text}
assert {str(p.relative_to(repo)):sha(p.read_bytes()) for p in repo.rglob('*') if p.is_file() and '.git' not in p.parts}==fixture_before
assert before=={label:source_hashes(base) for label,base in [('original',ORIGINAL),('candidate',CANDIDATE)]}
receipt={'status':'pass','purpose':'Real raw CP1252 hunks plus an unquoted UTF-8 path must be independent of CP1252 console text decoding.','python':sys.version,'candidateCliSha256':EXPECTED_CLI,'sourceBeforeAfter':before,'fixtureHashes':fixture_before,'rawDiffSha256':sha(raw),'previewCases':rows,'actualRun':{'status':report['status'],'final':report['final'],'tests_written':report['tests_written']},'commands':commands,'sourceAndFixtureUnchanged':True,'finished':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
(ROOT/'receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=True))
print(json.dumps({'status':'pass','previewCases':[{k:v for k,v in x.items() if k not in ['targets','stderr']} for x in rows],'realGeneratedTest':'passed','receiptSha256':sha((ROOT/'receipt.json').read_bytes())}))
