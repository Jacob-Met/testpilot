"""Read the frozen Windows packet; do not import or execute TestPilot."""
from pathlib import Path, PureWindowsPath
from collections import Counter
import hashlib, io, json, zipfile

ROOT = Path(__file__).parent
PACKET = Path('/dev/shm/testpilot-wheel-windows-1caa1d8e028a.zip')
KIT = Path('/dev/shm/hamon-1caa-testpilot-wheel/TestPilot-Scripted-Review-d2596c1a-20261013-v2.zip')
CUSTODY = Path('/dev/shm/testpilot-wheel-windows-1caa1d8e028a-custody.json')
def require(value, label):
    if not value:
        raise ValueError(label)
def sha(data):
    return hashlib.sha256(data).hexdigest()
def bound(data, record):
    return len(data) == record['bytes'] and sha(data) == record['sha256']
def text(response):
    return '\n'.join(x.get('text', '') for x in response.get('content', []))

packet_bytes, kit_bytes, custody_bytes = PACKET.read_bytes(), KIT.read_bytes(), CUSTODY.read_bytes()
require(sha(packet_bytes) == '306534cd2d94ecf32dca64013da75f54868bb7868a79720e1b1afd14c73fedee', 'packet pin')
require(sha(kit_bytes) == '8b3c856751ae9bd24b74474b68624e38e97d9157429aafc6c9d671676be00a4d', 'kit pin')
require(sha(custody_bytes) == '9e5f25dfab4b3d6f3a45d73e4d00cd136cc5d432570ca46acf243eb7e0ae6a3c', 'custody pin')
with zipfile.ZipFile(io.BytesIO(packet_bytes)) as packet, zipfile.ZipFile(io.BytesIO(kit_bytes)) as kit:
    require(packet.testzip() is None and kit.testzip() is None, 'CRCs')
    names = packet.namelist()
    manifest = json.loads(packet.read('MANIFEST.json'))
    require(len(names) == 27 and len(set(names)) == 27 and len(manifest['files']) == 26, 'packet membership')
    require(set(names) == {'MANIFEST.json'} | {x['path'] for x in manifest['files']}, 'manifest set')
    for record in manifest['files']:
        require(bound(packet.read(record['path']), record), 'payload ' + record['path'])
    require(packet.read('kit-MANIFEST.json') == kit.read('MANIFEST.json'), 'kit manifest equality')
    require(packet.read('kit-SOURCE_MANIFEST.json') == kit.read('SOURCE_MANIFEST.json'), 'source manifest equality')
    source = json.loads(kit.read('SOURCE_MANIFEST.json'))
    fresh = json.loads((ROOT/'fresh-git-pins.json').read_bytes())
    canonical = {x['path']: x for x in fresh['files']}
    require(fresh['commit'] == source['source_commit'] and fresh['tree'] == source['source_tree'], 'source identity')
    require(len(canonical) == len(source['files']) == 25, 'canonical source count')
    for record in source['files']:
        require(record['sha'] == canonical[record['path']]['sha'] and record['bytes'] == canonical[record['path']]['size'], 'source pin ' + record['path'])
    receipt = json.loads(packet.read('receiving/receipt.json'))
    require(receipt['outcome'] == 'PASS' and not receipt.get('error'), 'native outcome')
    require(receipt['input_guards_before'] == receipt['input_guards_after'] and len(receipt['input_guards_after']) == 36, '36 native input guards')
    require(receipt['installed_modules_before'] == receipt['installed_modules_after'] and len(receipt['installed_modules_after']) == 14, '14 native module guards')
    base = PureWindowsPath(receipt['capsule'])
    for name in kit.namelist():
        matching = [x for x in receipt['input_guards_after'] if PureWindowsPath(x['path']) == base/'packet'/name]
        require(len(matching) == 1 and bound(kit.read(name), matching[0]), 'kit input ' + name)
    with zipfile.ZipFile(io.BytesIO(kit.read('testpilot-0.1.0-py3-none-any.whl'))) as wheel:
        for record in receipt['installed_modules_after']:
            path = PureWindowsPath(record['path']).relative_to(base/'venv/Lib/site-packages').as_posix()
            data = wheel.read(path)
            require(bound(data, record), 'installed module ' + path)
            require(hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == canonical[path]['sha'], 'module Git blob ' + path)
    labels = ['create-venv','venv-pytest','install-wheel','installed-location','help','targets','scripted']
    require([x['label'] for x in receipt['calls']] == labels, 'seven operation identities')
    require([x['exit'] for x in receipt['calls']] == [0,0,0,0,0,0,1], 'seven exits')
    for call in receipt['calls']:
        for stream in ['stdout','stderr']:
            require(bound(packet.read('receiving/' + call['label'] + '.' + stream), call[stream]), 'raw stream binding')
        require(packet.read('receiving/' + call['label'] + '.stderr') == b'', 'empty stderr')
    capability = json.loads(packet.read('receiving/venv-pytest.stdout'))
    require(capability == receipt['venv_capability'] and capability['pytest_version'] == '9.0.2' and capability['user_site_enabled'] is True, 'actual pytest prerequisite')
    require(PureWindowsPath(capability['prefix']) == base/'venv', 'venv prefix')
    location = json.loads(packet.read('receiving/installed-location.stdout'))
    require(PureWindowsPath(location['module']) == base/'venv/Lib/site-packages/testpilot/__init__.py', 'installed package location')
    targets = json.loads(packet.read('receiving/targets.stdout'))
    require(targets == json.loads(kit.read('receiving/targets.stdout.txt')), 'target equality')
    require(len(targets['changed_functions']) == 1 and targets['changed_functions'][0]['qualname'] == 'clamp', 'exact target')
    report = json.loads(packet.read('sample-result/report.json'))
    final = report['final']
    require(report['status'] == 'suspected_code_bug' and report['tests_written'] == 4, 'sample outcome')
    require(final['returncode'] == 1 and not final['timed_out'] and final['junit_available'], 'sample execution')
    require((final['passed'], final['failed'], final['errors'], final['skipped']) == (3,3,0,0), 'sample totals')
    require(Counter(x['outcome'] for x in final['cases']) == {'passed':3,'failed':3}, 'six actual case outcomes')
    require(final['generated'] == {'collected':4,'passed':1,'failed':3,'error':0,'skipped':0}, 'generated totals')
    require(report['test_files'] == json.loads(kit.read('recorded-result/report.json'))['test_files'], 'generated source equality')
    require(packet.read('sample-result/testpilot.patch').decode().replace('\r\n','\n') == kit.read('recorded-result/testpilot.patch').decode().replace('\r\n','\n'), 'normalized patch equality')
    for record in receipt['result']['files']:
        require(bound(packet.read('sample-result/' + PureWindowsPath(record['path']).name), record), 'saved report identity')
    require(receipt['temporary_entries'] == [], 'owned temporary directory empty')
    routing = json.loads(packet.read('routing.json'))
    completion = text(routing['controller_completion'])
    require('Process completed with exit code 0' in completion and sha(packet.read('receiving/receipt.json')) in completion, 'routed native completion')
    custody = json.loads(custody_bytes)
    require(bound(packet_bytes, custody['artifact']), 'export identity')
    require('Process completed with exit code 0' in text(custody['export_completion']), 'export completion')
    require(any('Process completed with exit code 0' in x for x in custody['readback']['completion']), 'readback completion')
    result = {'status':'PASS','scope':'Independent read-only artifact/source/receipt/guide review; no product execution, installation or tests repeated','accepted_source':source['source_commit'],'accepted_tree':source['source_tree'],'archive':{'bytes':len(packet_bytes),'sha256':sha(packet_bytes),'members':27,'payloads':26},'receipt_sha256':sha(packet.read('receiving/receipt.json')),'kit_sha256':sha(kit_bytes),'verified':{'fresh_canonical_pins':25,'exact_kit_members':31,'unchanged_native_input_guards':36,'exact_unchanged_installed_modules':14,'raw_operation_pairs':7,'exits':[0,0,0,0,0,0,1],'case_outcomes':{'passed':3,'failed':3,'generated':4},'target_and_generated_source_equal_cloud':True,'patch_equal_after_CRLF_normalization':True},'guide_review':'The actual ordinary user-site-aware venv route omits -I, uses only existing pytest and a local wheel, distinguishes argument-list execution from CMD examples, and states historical-source, no browser and no maintained-suite limits. No blockers found.','qualification_limits':['Native Windows original MSI edc endpoint only; no existing estate installation replaced.','Full raw reports differ from cloud due platform diagnostics, timings and native newlines.','No live model/provider, current-main compatibility, full test suite, interruption or browser claim.','Routing retains the isolated capability start response but no separate completion for that preliminary capability probe; actual consumer, export and archive readback completions are retained.'],'verification_script_sha256':sha(Path(__file__).read_bytes())}
    (ROOT/'independent-review.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
