"""Verify retained ThinkPad receiving evidence; never install or rerun tests."""
import argparse, hashlib, json, zipfile
from pathlib import Path

def verify(target, wheel=None):
    p=Path(target)
    if p.is_file():
        z=zipfile.ZipFile(p); assert z.testzip() is None
        names=z.namelist(); read=z.read
    else:
        names=[f.relative_to(p).as_posix() for f in p.rglob('*') if f.is_file()]
        read=lambda n:(p/n).read_bytes()
    assert len(names)==len(set(names))
    sha=lambda b:hashlib.sha256(b).hexdigest()
    manifest=json.loads(read('MANIFEST.json'))['files']
    assert set(names)==set(manifest)|{'MANIFEST.json'}
    for n,v in manifest.items():
        b=read(n); assert len(b)==v['bytes'] and sha(b)==v['sha256'], n
    prefix='evidence/native/'
    get=lambda n:json.loads(read(prefix+n))
    inner=get('MANIFEST.json')['files']
    assert {n[len(prefix):] for n in names if n.startswith(prefix)}==set(inner)|{'MANIFEST.json'}
    for n,v in inner.items():
        b=read(prefix+n); assert len(b)==v['bytes'] and sha(b)==v['sha256']
    final=get('native_receiving-v2.json'); original=get('native_receiving.json')
    course=get('course-v1/receiving.json'); source=get('SOURCE_PROVENANCE.json')
    assert final['status']=='qualified_isolated_native_install'
    assert final['source_commit']==source['source_commit']=='f27ad21fa1f130e74defdda4403028d3ed11806e'
    expected={x['path']:x['sha256'] for x in source['files'] if x['path'].startswith('testpilot/') and x['path'].endswith('.py')}
    assert len(expected)==16 and expected==final['installed_module_sha256']==course['composed_source_sha256']
    assert original['status']=='failed' and original['error']=='AssertionError: testpilot 0.1.0\n'
    assert all(c['exit_code']==0 for c in original['commands']+final['commands'])
    assert read(prefix+'version.stdout')==read(prefix+'console-version.stdout')==b'testpilot 0.1.0\n'
    assert final['base_distributions_preserved']=={'pytest':'9.0.2','coverage':None,'pip':None,'testpilot':None}
    assert course['status']=='ACCEPT' and course['repair_rounds_used']==1 and course['failed_generated_round']==1
    for key in ('legacy_case_admitted','progress_phase_notices_received','final_diagnostic_retained','original_project_unchanged','adopted_originals_unchanged'):
        assert course[key] is True, key
    assert course['recheck_model_calls']==0 and course['raw_noise_bytes_per_existing_test']==16777216
    for rel in ('generated/report.json','recheck/recheck.json'):
        report=get('course-v1/'+rel)
        assert report['status']=='passed'
        f=report['final']; assert f['returncode']==0 and f['passed']==3 and f['failed']==f['errors']==f['skipped']==0
        assert len(f['output'])<=3000 and 'ESTATE-NATIVE-FINAL-DIAGNOSTIC' in f['output']
        assert len(f['cases'])==3 and all(x['outcome']=='passed' for x in f['cases'])
    assert get('course-v1/recheck/recheck.json')['model_calls']==0
    for n,v in course['artifacts'].items():
        b=read(prefix+'course-v1/'+n); assert len(b)==v['bytes'] and sha(b)==v['sha256']
    for item in course['retained_tests']:
        b=read(prefix+'course-v1/adopted-project/'+item['path'])
        assert len(b)==item['bytes'] and sha(b)==item['sha256'] and item['placement']=='already_present'
    for n in ('calculator.py','legacy/test_legacy.py','selected/test_existing.py'):
        assert read(prefix+'course-v1/project/'+n)==read(prefix+'course-v1/adopted-project/'+n)
    wheel_checked=False
    if wheel:
        raw=Path(wheel).read_bytes()
        assert len(raw)==78834 and sha(raw)==final['wheel_sha256']=='cdb743f38fc17fd4caee4f3d0d98761cf8495f8992e2cbb5703444674578f54d'
        with zipfile.ZipFile(wheel) as wz:
            assert len(wz.namelist())==23
            assert {n:sha(wz.read(n)) for n in expected}==expected
        wheel_checked=True
    return {'status':'verified','payloads':len(manifest),'native_payloads':len(inner),'installed_modules':16,'generation_passed':3,'recheck_passed':3,'recheck_model_calls':0,'external_wheel_checked':wheel_checked,'product_source':final['source_commit']}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target',nargs='?',default=Path(__file__).resolve().parent)
    parser.add_argument('--wheel',type=Path)
    args=parser.parse_args()
    print(json.dumps(verify(args.target,args.wheel),indent=2))
