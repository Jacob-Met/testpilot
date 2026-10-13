"""Independently install the received wheel and recheck retained tests outside source."""
import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--wheel',required=True,type=Path)
    p.add_argument('--source',required=True,type=Path)
    p.add_argument('--python',required=True)
    p.add_argument('--provider',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    raw=a.wheel.read_bytes()
    assert len(raw)==78834 and digest(raw)=='cdb743f38fc17fd4caee4f3d0d98761cf8495f8992e2cbb5703444674578f54d'
    source={f.name:digest(f.read_bytes()) for f in (a.source/'testpilot').glob('*.py')}
    assert len(source)==16
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.testzip() is None
        modules={Path(n).name:digest(z.read(n)) for n in z.namelist() if n.startswith('testpilot/') and n.endswith('.py')}
        assert modules==source
        records=list(csv.reader(io.StringIO(z.read('testpilot-0.1.0.dist-info/RECORD').decode())))
        for name,encoded,size in records:
            if encoded:
                assert encoded.startswith('sha256=')
                data=z.read(name)
                assert len(data)==int(size)
                assert base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')==encoded.split('=',1)[1]
    assert not (a.provider/'testpilot').exists()
    commands=[]
    with tempfile.TemporaryDirectory(prefix='testpilot-wheel-independent-',dir='/dev') as temp:
        root=Path(temp);env=os.environ.copy();env.pop('PYTHONPATH',None)
        env.update(PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(root),TESTPILOT_BACKEND='invalid-provider',TESTPILOT_BASE_URL='http://127.0.0.1:1')
        def call(label,argv):
            result=subprocess.run(argv,cwd=root,env=env,capture_output=True,timeout=60)
            commands.append({'label':label,'argv':[str(x) for x in argv],'exit':result.returncode,'stdout':result.stdout.decode(),'stderr':result.stderr.decode()})
            assert result.returncode==0,(label,result.stdout,result.stderr)
            return result.stdout
        venv=root/'venv'
        call('fresh-owned-venv',[a.python,'-I','-B','-m','venv',str(venv)])
        py=venv/'bin/python'
        call('offline-wheel-install',[str(py),'-I','-B','-m','pip','install','--no-index','--no-deps','--no-cache-dir',str(a.wheel)])
        site=next((venv/'lib').glob('python*/site-packages'))
        (site/'received-pytest-provider.pth').write_text(str(a.provider)+'\n')
        installed=site/'testpilot'
        assert {f.name:digest(f.read_bytes()) for f in installed.glob('*.py')}==source
        probe=json.loads(call('isolated-installed-identity',[str(py),'-I','-B','-c','import json,testpilot,pytest; print(json.dumps({"path":testpilot.__file__,"version":testpilot.__version__,"pytest":pytest.__version__}))']))
        assert Path(probe['path']).parent==installed and probe['version']=='0.1.0'
        assert call('isolated-version',[str(py),'-I','-B','-m','testpilot','--version'])==b'testpilot 0.1.0\n'
        assert call('installed-console-entrypoint',[str(venv/'bin/testpilot'),'--version'])==b'testpilot 0.1.0\n'
        assert b'--progress' in call('isolated-run-help',[str(py),'-I','-B','-m','testpilot','run','--help'])
        project=root/'project';project.mkdir();(project/'compute.py').write_text('def square(x):\n    return x*x\n')
        test='from compute import square\ndef test_retained():\n    assert square(9) == 81\n'
        report=root/'saved.json';report.write_text(json.dumps({'status':'historical','test_files':{'tests/test_retained.py':test}}))
        original=report.read_bytes();project_before={str(f.relative_to(project)):digest(f.read_bytes()) for f in project.rglob('*') if f.is_file()}
        output=root/'recheck'
        call('actual-isolated-installed-recheck',[str(py),'-I','-B','-m','testpilot','recheck','--repo',str(project),'--report',str(report),'--out',str(output),'--python',str(py),'--timeout','20'])
        result=json.loads((output/'recheck.json').read_bytes())
        assert result['status']=='passed' and result['model_calls']==0
        assert result['final']['passed']==1 and result['final']['generated']['passed']==1
        assert result['test_files']=={'tests/test_retained.py':test}
        assert result['source_report']['sha256']==digest(original)
        assert report.read_bytes()==original
        assert project_before=={str(f.relative_to(project)):digest(f.read_bytes()) for f in project.rglob('*') if f.is_file()}
        assert {f.name:digest(f.read_bytes()) for f in installed.glob('*.py')}==source
        artifacts={f.name:{'bytes':f.stat().st_size,'sha256':digest(f.read_bytes())} for f in output.iterdir()}
    assert {f.name:digest(f.read_bytes()) for f in (a.source/'testpilot').glob('*.py')}==source
    receipt={'status':'ACCEPT','source_commit':'f27ad21fa1f130e74defdda4403028d3ed11806e','wheel_sha256':digest(raw),'wheel_bytes':len(raw),'wheel_record_entries_verified':len(records),'exact_source_wheel_installed_modules':modules,'fresh_install':True,'installed_identity':probe,'read_only_pytest_provider':str(a.provider),'commands':commands,'native_recheck':result,'outputs':artifacts,'source_report_project_and_modules_preserved':True,'limits':'Fresh disposable POSIX venv, local wheel with no dependency downloads; pytest comes from explicit read-only qualified provider. Isolated -I module execution outside source/no PYTHONPATH plus console entrypoint. One retained-test recheck; no repeated generation flood, Windows or existing-estate installation claim.'}
    print(json.dumps({'status':'ACCEPT','installed_modules':16,'native_recheck_passes':1,'model_calls':0,'pytest':probe['pytest']}))
    (a.out/'receiving.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':
    main()
