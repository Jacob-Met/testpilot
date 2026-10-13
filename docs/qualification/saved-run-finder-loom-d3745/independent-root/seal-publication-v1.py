"""Seal original independent evidence; no product or Git execution."""
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import stat

BASE=Path('/workspace/scratch/d3745ea0f44f')
ROOT=BASE/'root-testpilot-history'
ORACLES=ROOT/'oracles'
AUTHOR=BASE/'loom-testpilot-history'
PREFIX='docs/qualification/saved-run-finder-loom-d3745/independent-root/'

def identity(raw):
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'git_blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}

def write_new(path,raw):
    with path.open('xb') as f:f.write(raw)

def dump(value):return (json.dumps(value,indent=2)+'\n').encode()

raw=(ORACLES/'case-spec-v1.json').read_bytes()
if identity(raw)['sha256']!='6793d9d1466011524f7541c321231f3be78a20addd3170cca257bfd93c07cdbf':
    raise ValueError('Original case specification changed')
compressed=gzip.compress(raw,compresslevel=9,mtime=0)
if gzip.decompress(compressed)!=raw:raise ValueError('Compressed transport differs')
write_new(ORACLES/'case-spec-v1.json.gz',compressed)
binding={'schema':'hamon.root.testpilot-history.compressed-input-spec.v1','original':identity(raw),
         'gzip':identity(compressed),'gzip_mtime':0,'decompressed_byte_equality':True,
         'scope':'Transport of the original exact spec only; original receiver/input/oracle bodies unchanged. No product execution.'}
write_new(ORACLES/'compressed-spec-binding-v1.json',dump(binding))
spec=json.loads(raw)
selection=[(n,ROOT/n) for n in ['README.md','receiving-criteria-v1.md','receive-history-v1.py','freeze-v1.json',
    'source-review-v1.json','review-source-v1.py','seal-publication-v1.py','course-v1.stdout','course-v1.stderr','received-v1/receipt.json']]
selection += [(f'oracles/{n}',ORACLES/n) for n in ['provenance-v1.json','case-summary-v1.json','public-clarification-v1.json','case-spec-v1.json.gz','compressed-spec-binding-v1.json']]
selection += [('oracles/generator-v1.py',BASE/'anvil/build-history-oracles-v1.py')]
selection += [(f'oracles/seeds/{n}.json',ORACLES/'seeds'/(n+'.json')) for n in ['calc_clamp','stats_median','synthetic-minimal','synthetic-unicode','synthetic-recheck']]
selection += [(f'public-contract/{n}',AUTHOR/'preparation'/n) for n in ['public-contract-v1.md','public-contract-v1-addendum.json','public-contract-v1-addendum-v2.json']]
selection += [(f'candidate-offer/{n}',AUTHOR/n) for n in ['candidate-freeze-v2.json','candidate-receiving-manifest-v2.json']]
selection += [('peer-reviews/loom-controller-v1.json',Path('/dev/shm/loom-d3745-reviews/testpilot-history-receiver-review-v1.json')),
              ('peer-reviews/forge-controller-v1.json',BASE/'forge/reviews/testpilot-history-controller-review-v1.json'),
              ('peer-reviews/forge-source-v1.json',BASE/'forge/reviews/testpilot-history-source-review-v1.json')]
for c in spec['cases']:
    selection.append(('oracles/expected/'+c['name']+'.stdout',Path(c['expected_stdout_path'])))
    for stream in ['stdout.bin','stderr.bin']:
        rel='received-v1/'+c['name']+'/'+stream
        selection.append((rel,ROOT/rel))
if len({p for p,_ in selection})!=len(selection):raise ValueError('Duplicate selection')
rows=[]
for dest,path in selection:
    if path.is_symlink() or not path.is_file():raise ValueError('Nonregular original input')
    body=path.read_bytes();mode=stat.S_IMODE(path.stat().st_mode)
    rows.append({'path':dest,'source_path':str(path),'mode':'100644','native_mode':mode,**identity(body)})
descriptor={'schema':'hamon.root.testpilot-history.independent-publication.v1','prefix':PREFIX,
            'created':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':rows,
            'scope':'Original accepted34-command independent CLI course and pre-exposure controls, with byte-exact compressed original input spec; no repeated execution or changed predicates.'}
target=ROOT/'independent-publication-inputs-v1.json'
write_new(target,dump(descriptor))
print(json.dumps({'descriptor':identity(target.read_bytes()),'files':len(rows),'payload_bytes':sum(r['bytes'] for r in rows),'compressed_spec':identity(compressed)}))
