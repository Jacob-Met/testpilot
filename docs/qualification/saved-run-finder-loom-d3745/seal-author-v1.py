"""Seal explicit historical author evidence without executing TestPilot."""
from pathlib import Path
import hashlib
import json
import stat
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PREFIX = 'docs/qualification/saved-run-finder-loom-d3745/author/'

def sha(body):
    return hashlib.sha256(body).hexdigest()

def blob(body):
    return hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()

def encode(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('ascii')

files = []
def add(source, destination):
    p = Path(source)
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode)
    b = p.read_bytes()
    files.append({'path': destination, 'source_path': str(p), 'mode': '100644',
                  'native_mode': stat.S_IMODE(s.st_mode), 'bytes': len(b),
                  'sha256': sha(b), 'git_blob': blob(b)})

for directory in ['preparation', 'original-observation-v1', 'author-tests-v1',
                  'author-qualification-v1', 'author-read-bound-v2']:
    for p in sorted((ROOT / directory).iterdir()):
        assert p.is_file()
        destination = ('README.md' if p.name == 'README-author.md'
                       else directory + '/' + p.name)
        add(p, destination)
for name in ['candidate-freeze-v1.json', 'candidate-freeze-v2.json',
             'candidate-receiving-manifest-v2.json']:
    add(ROOT / name, name)
add(ROOT / 'candidate/testpilot/history.py', 'received-v1/history.py')
assert len(files) == 46
assert len({r['path'] for r in files}) == len(files)
value = {'schema': 'hamon.loom.testpilot-history.author-publication.v1',
         'prefix': PREFIX, 'created': datetime.now(timezone.utc).isoformat(),
         'scope': 'Original refusal, original V1 author courses, final V2 single-line raw-read correction and distinct focused course. Historical paths and unpublished state preserved.',
         'files': files}
body = encode(value)
out = HERE / 'author-publication-inputs-v1.json'
out.open('xb').write(body)
print(json.dumps({'path': str(out), 'bytes': len(body), 'sha256': sha(body),
                  'git_blob': blob(body), 'rows': len(files),
                  'payload_bytes': sum(r['bytes'] for r in files)}))
