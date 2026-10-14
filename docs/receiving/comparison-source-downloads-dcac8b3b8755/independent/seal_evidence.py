"""Join completed exact evidence without rerunning a product or browser."""
from pathlib import Path
import base64, hashlib, json
r=Path(__file__).resolve().parent
def ident(p):
    b=p.read_bytes()
    return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
criteria=json.loads((r/'criteria.json').read_bytes()); counts={}
for mode,n in [('original',80),('candidate',218)]:
    p=r/f'native-{mode}/{mode}-browser-v1/receiving.json';raw=json.loads(p.read_bytes())
    assert raw['passed'] and raw['preserved'] and raw['before']==raw['after']
    assert len(raw['checks'])==n and all(x['actual']==x['expected'] and x['passed'] for x in raw['checks'])
    assert raw['context_closed'] and raw['managed_disconnect'] and raw['playwright_stopped']
    for name,pin in raw['artifacts'].items():assert ident(p.parent/name)==pin
    for case,pair in criteria['cases'].items():
        for role,fixture in zip(['before','after'],pair):assert (p.parent/f'{case}-{role}-{role}-report.json').read_bytes()==(r/'fixtures'/fixture).read_bytes()
    producer=json.loads((r/f'{mode}-producer-v1/receiving.json').read_bytes())
    assert producer['passed'] and producer['preserved']
    for prefix in ['source','fixtures','watched']:assert producer[prefix+'_before']==producer[prefix+'_after']
    assert all(x['actual']==x['expected'] and x['passed'] for x in producer['checks'])
    for child in producer['children']:
        for stream in ['stdout','stderr']:
            actual=ident(r/f'{mode}-producer-v1'/f"{child['case']}.{stream}.txt")
            assert actual=={k:child[stream][k] for k in actual}
    counts[mode]={'browser_checks':len(raw['checks']),'downloads':len(raw['downloads']),'producer_checks':len(producer['checks']),'children':[x['returncode'] for x in producer['children']]}
for f in criteria['files']:
    for role in ['before','after']:
        v=f[role]
        if v['state']=='download':
            p=r/'native-candidate/candidate-browser-v1'/f"file{f['index']}-{role}-{v['filename']}"
            assert p.read_bytes()==base64.b64decode(v['base64'],validate=True)
old=json.loads((r/'native-original/original-browser-v1/receiving.json').read_bytes())
new=json.loads((r/'native-candidate/candidate-browser-v1/receiving.json').read_bytes())
assert old['fixed']==new['fixed']
selected=[r/n for n in ['freeze_inputs.py','criteria.json','produce_pages.py','receive_browser.py','preflight.py','original-process-records.json','candidate-process-records.json','export-process-records.json','native-transfer-reconciliation.json','visual-review.json','RECEIVING.md','seal_evidence.py','original-producer.stdout.txt','original-producer.stderr.txt']]
selected+=sorted((r/'fixtures').iterdir())
for mode in ['original','candidate']:
    selected+=sorted(p for p in (r/f'{mode}-producer-v1').iterdir() if p.is_file())
    selected+=sorted(p for p in (r/f'native-{mode}').rglob('*') if p.is_file())
selected+=sorted((r/'candidate-producer-refused-existing-v1').iterdir())
assert len(selected)==len(set(selected))
rows=[{'path':p.relative_to(r).as_posix(),**ident(p)} for p in sorted(selected)]
manifest={'schema':'hamon.selected-evidence/1','repository':'Jacob-Met/testpilot','issue':130,'source':'941c81c710e2742498fa3748a939434420b89fb2','observer':'f8c96085e148a2996ed036fb7f50fcec543c212e','counts':counts,'files':rows,'bytes':sum(x['bytes'] for x in rows),'limits':'No product/browser replay. Exact native raw files are not reserialized. Projected source, profiles and transport carriers excluded; source packets supplied once by owner at parent receiving root.'}
p=r/'publication-manifest.json'
with p.open('x',encoding='utf-8') as out:out.write(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'files':len(rows),'bytes':manifest['bytes'],'manifest':ident(p),'counts':counts}))
