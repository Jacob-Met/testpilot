from pathlib import Path
import hashlib
import io
import json
import zipfile

r = Path('/dev/shm/hamon-1caa-testpilot-wheel')
pub = r/'publication/docs/receiving/scripted-wheel-1caa1d8e028a'
pins = {x['path']:x['sha'] for x in json.loads(Path('/dev/shm/hamon-1caa-testpilot-source-review-pins.json').read_text())}
sha = lambda b: hashlib.sha256(b).hexdigest()
kit = r/'TestPilot-Scripted-Review-d2596c1a-20261013-v2.zip'
data = kit.read_bytes()
assert sha(data)=='8b3c856751ae9bd24b74474b68624e38e97d9157429aafc6c9d671676be00a4d'
with zipfile.ZipFile(io.BytesIO(data)) as z:
    assert z.testzip() is None and len(z.namelist())==len(set(z.namelist()))==31
    manifest = json.loads(z.read('MANIFEST.json'))
    source = json.loads(z.read('SOURCE_MANIFEST.json'))
    assert len(manifest['files'])==30 and len(source['files'])==25
    assert source['source_tree']=='3b6d270f655310fa2f98cab9bccffca23ec146cf'
    assert set(z.namelist())=={x['path'] for x in manifest['files']}|{'MANIFEST.json'}
    for x in manifest['files']:
        b = z.read(x['path'])
        assert len(b)==x['bytes'] and sha(b)==x['sha256']
    for x in source['files']:
        b = (r/'source'/x['path']).read_bytes()
        assert len(b)==x['bytes'] and sha(b)==x['sha256']
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+bytes([0])+b).hexdigest()==x['sha']==pins[x['path']]
    wheel = z.read('testpilot-0.1.0-py3-none-any.whl')
    assert len(wheel)==75206 and sha(wheel)=='c471d961e1b26051209b2d8bdcf0629b1f0185b25ae6c0d0d733bacca344d246'
    with zipfile.ZipFile(io.BytesIO(wheel)) as w:
        assert w.testzip() is None
        modules = [n for n in w.namelist() if n.startswith('testpilot/') and n.endswith('.py')]
        assert len(modules)==14
        installed = r/'installed-env/lib/python3.12/site-packages'
        after = []
        for n in modules:
            b = w.read(n)
            p = installed/n
            assert b==(r/'source'/n).read_bytes()==p.read_bytes()
            s = p.stat()
            after.append({'path':n,'bytes':len(b),'sha256':sha(b),'mtime_ns':s.st_mtime_ns,'inode':s.st_ino,'mode':s.st_mode})
    for n in z.namelist():
        if n.startswith('sample/'):
            assert z.read(n)==(r/'source/eval/cases/calc_clamp'/n.removeprefix('sample/')).read_bytes()
    receipt = json.loads(z.read('receiving/consumer-receipt.json'))
    assert receipt['sample_before']==receipt['sample_after']
    assert [(x['name'],x['exit_code']) for x in receipt['commands']]==[('help',0),('targets',0),('scripted',1)]
    for x in receipt['commands']:
        assert z.read('receiving/'+x['name']+'.stdout.txt').decode()==x['stdout']
        assert z.read('receiving/'+x['name']+'.stderr.txt').decode()==x['stderr']==''
    report = json.loads(z.read('recorded-result/report.json'))
    assert report['status']=='suspected_code_bug'
    final = report['final']
    assert final['returncode']==1 and not final['ok']
    assert (final['passed'],final['failed'],final['errors'],final['skipped'])==(3,3,0,0)
    assert (final['generated']['collected'],final['generated']['passed'],final['generated']['failed'])==(4,1,3)
    for n,x in receipt['outputs'].items():
        b = z.read('recorded-result/'+n)
        assert len(b)==x['bytes'] and sha(b)==x['sha256']
    v1 = json.loads((pub/'kit-receipt.json').read_text())
    with zipfile.ZipFile(Path(v1['zip'])) as old:
        assert set(old.namelist())==set(z.namelist())
        changed = [n for n in z.namelist() if old.read(n)!=z.read(n)]
        assert sorted(changed)==['MANIFEST.json','SOURCE_MANIFEST.json']
        assert json.loads(old.read('SOURCE_MANIFEST.json'))['source_tree']==source['source_commit']
review = {
    'result':'PASS', 'reviewer':'1caa1d8e028a/source_delivery',
    'scope':'Read-only guide/source/recorded artifact review; no consumer or native rerun',
    'source_commit':source['source_commit'], 'source_tree':source['source_tree'],
    'kit_sha256':sha(data), 'kit_bytes':len(data), 'all31archive_members_checked':True,
    'all30manifest_payloads_checked':True, 'all25source_blobs_match_fresh_remote_tree':True,
    'wheel_modules':14, 'installed_modules_after_recorded_run_byte_exact':after,
    'cloud_recorder_note':'Archived receiver verifies module bytes before commands but does not itself recheck them afterward. This independent review now verifies all14 still match wheel and accepted source after the recorded run; no module changed.',
    'three_actual_recorded_exit_codes':[0,0,1],
    'actual_final_tests':{'passed':3,'failed':3,'generated_collected':4,'generated_passed':1,'generated_failed':3},
    'four_recorded_reports_match_receipt':True, 'sample_inputs_byte_and_metadata_guard_pass':True,
    'v1_to_v2_only_two_manifest_members_changed':changed,
    'guide_default_interpreter_checked':'CLI --python defaults to this interpreter via sandbox python or sys.executable; portable omission is equivalent to recorder explicit installed python.',
    'guide_claims':'Accurate scripted provider, intentionally broken clamp, no passing patch claim, Python/pytest prerequisites not bundled, existing dependencies/no downloads, cloud-only limits, shared package version tied to source hash.',
    'earlier_readonly_review_attempt':'Review-only Git hash computation first used an incorrectly escaped NUL prefix and stopped at its own assertion. No source/artifact mutation or consumer execution occurred. Correct prefix bytes([0]) matches all25 source blobs; no product defect.',
    'pending':'Native raw custody review belongs project worker; this read-only review does not claim it. Fresh publication ownership/workflows/tree fence still required.'
}
path = Path('/dev/shm/hamon-1caa-testpilot-source-delivery-review.json')
path.write_text(json.dumps(review,indent=2)+chr(10))
print(json.dumps({'result':'PASS','path':str(path),'sha256':sha(path.read_bytes()),'source_blobs':25,'installed_modules_after':14,'kit_members':31}))
