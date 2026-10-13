"""Independent actual CLI receiving of the joined TestPilot increments.

No provider calls, PID-table assumptions, production monkeypatching or source
changes. The intentionally failing legacy test is outside ancestor testpaths.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def files(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}

def wait(predicate, child, timeout=10):
    until = time.monotonic() + timeout
    while not predicate():
        assert child.poll() is None, ('early CLI exit', child.returncode)
        assert time.monotonic() < until, 'native barrier timeout'
        time.sleep(.01)

FIXTURE = '''import os
from pathlib import Path
import time
from calculator import double

def test_existing(capfd):
    d=Path(os.environ['TP_TOOLKIT_CONTROL'])
    d.joinpath('entered').write_text('entered')
    until=time.monotonic()+20
    while not d.joinpath('release').exists():
        if d.joinpath('challenge').exists():
            d.joinpath('ack.new').write_text(d.joinpath('challenge').read_text())
            d.joinpath('ack.new').replace(d/'ack')
        assert time.monotonic()<until
        time.sleep(.01)
    with capfd.disabled():
        for _ in range(256):
            pending=memoryview(b'x'*65536)
            while pending:
                pending=pending[os.write(1,pending):]
        os.write(2,b'\\nINDEPENDENT-TOOLKIT-FINAL-DIAGNOSTIC\\n')
    assert double(21)==42
'''

def semantic(report):
    return {k: report[k] for k in ('status','ok','repair_rounds_used','patch','ledger','test_files','plan')} | {
        'final': {k:report['final'][k] for k in ('returncode','passed','failed','errors','skipped','generated','junit_available','timed_out')}
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--separate-progress',type=Path,required=True)
    ap.add_argument('--combined',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args(); root=a.out.resolve();root.mkdir(parents=True,exist_ok=False)
    project=root/'project';responses=root/'responses';tmp=root/'native-tmp'
    for p in (project/'tests',project/'legacy',responses,tmp):p.mkdir(parents=True)
    (root/'pytest.ini').write_text('[pytest]\ntestpaths = tests\n')
    (project/'calculator.py').write_text('def double(value):\n    return value * 2\n')
    (project/'tests/test_existing.py').write_text(FIXTURE)
    (project/'legacy/test_required.py').write_text("import os\ndef test_required_legacy():\n    assert os.environ['TP_TOOLKIT_LEGACY_PASS']=='1', 'REQUIRED-LEGACY-FAILURE'\n")
    diff=root/'change.diff';diff.write_text('--- /dev/null\n+++ b/calculator.py\n@@ -0,0 +1,2 @@\n+def double(value):\n+    return value * 2\n')
    (responses/'01.txt').write_text('PRIVATE-CONTENT: check double while preserving all existing tests.')
    for n,v in ((2,7),(3,6)):
        (responses/f'{n:02}.txt').write_text('```python path=tests/test_generated.py\nfrom calculator import double\ndef test_generated():\n    assert double(3)=='+str(v)+'\n```\n')
    original=files(project);source_hashes=files(a.combined/'testpilot')
    cases=[]
    sequence=[('separate_false_pass',a.separate_progress,True,False),
              ('combined_detects_failure',a.combined,True,False),
              ('combined_quiet',a.combined,False,True),
              ('combined_progress',a.combined,True,True)]
    for label,source,progress,legacy_pass in sequence:
        dest=root/label;dest.mkdir();control=dest/'control';control.mkdir();out=dest/'report'
        env={k:v for k,v in os.environ.items() if not k.startswith('TESTPILOT_')}
        env.update(PYTHONPATH=str(source.resolve()),PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(tmp),
                   TP_TOOLKIT_CONTROL=str(control),TP_TOOLKIT_LEGACY_PASS=str(int(legacy_pass)))
        command=[sys.executable,'-B','-m','testpilot','run','--repo',str(project),'--diff',str(diff),
                 '--backend','scripted','--script',str(responses),'--rounds','1','--timeout','15','--no-coverage','--out',str(out)]
        if progress:command.append('--progress')
        start=time.monotonic()
        with (dest/'stdout.txt').open('wb') as stdout,(dest/'stderr.txt').open('wb') as stderr:
            child=subprocess.Popen(command,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
            try:
                wait(lambda:(control/'entered').exists(),child)
                (control/'challenge').write_text(label)
                wait(lambda:(control/'ack').exists() and (control/'ack').read_text()==label,child)
                assert not out.exists()
                assert (dest/'stdout.txt').read_text()==''
                early=(dest/'stderr.txt').read_text()
                assert early==('[testpilot] Baseline pytest: running\n' if progress else '')
                (control/'release').write_text('release')
                child.wait(timeout=35)
            finally:
                (control/'release').write_text('cleanup')
                if child.poll() is None:child.kill();child.wait(timeout=5)
        r=json.loads((out/'report.json').read_text());f=r['final']
        if label=='separate_false_pass':
            assert r['ok'] and f['passed']==2 and f['failed']==0
        elif label=='combined_detects_failure':
            assert not r['ok'] and f['passed']==2 and f['failed']==1
            assert 'REQUIRED-LEGACY-FAILURE' in f['output']
        else:
            assert r['ok'] and f['passed']==3 and f['failed']==0
        assert f['generated']['passed']==1 and r['repair_rounds_used']==1
        assert 'INDEPENDENT-TOOLKIT-FINAL-DIAGNOSTIC' in f['output'] and len(f['output'])<=3000
        assert '[testpilot]' not in (dest/'stdout.txt').read_text()
        if not progress:assert (dest/'stderr.txt').read_text()==''
        assert files(project)==original
        cases.append({'label':label,'progress':progress,'legacy_pass':legacy_pass,'returncode':child.returncode,
                      'live_held_stderr':early,'native_barrier_acknowledged':True,'semantics':semantic(r),
                      'final_saved_output_chars':len(f['output']),'elapsed_s':time.monotonic()-start})
        print(label,'ACCEPT',flush=True)
    assert cases[2]['semantics']==cases[3]['semantics']
    assert files(a.combined/'testpilot')==source_hashes
    receipt={'status':'ACCEPT','observed_at_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,
             'cases':cases,'source_sha256':source_hashes,'source_and_inputs_preserved':True,
             'quiet_progress_results_patch_and_accounting_equal':True,'native_output_bytes_per_existing_test':16*1024*1024,
             'limits':['Actual POSIX scripted CLI. No new memory-peak, Windows, installed-estate or adoption claim.',
                       'Source composition is local until exact published branch is independently read back.']}
    (root/'receiving.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':'ACCEPT','cases':len(cases),'quiet_progress_equal':True}))

if __name__=='__main__':main()
