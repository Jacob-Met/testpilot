"""Admit explicit finder source and historical evidence; no product execution."""
import base64
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ROOT_REVIEW = ROOT.parent / 'root-testpilot-history'
TOOLS = Path('/dev/shm/loom-d3745-fanout-comparison-html/publication/tools')
PREFIX = 'docs/qualification/saved-run-finder-loom-d3745/'
BASE = 'f9ba2d2260f7aa93b3958661aa178ad418df9af6'
TREE = '6aec92096d7786defc448dc2e5adba838771bcfd'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def blob(b):
    return hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()

def encode(x):
    return (json.dumps(x, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode('ascii')

def identity(p):
    p = Path(p)
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode), str(p)
    b = p.read_bytes()
    return {'source_path': str(p), 'native_mode': stat.S_IMODE(s.st_mode),
            'bytes': len(b), 'sha256': sha(b), 'git_blob': blob(b), 'mode': '100644'}

def capture(r):
    p = Path(r.get('mirror_path', r['source_path']))
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode), str(p)
    b = p.read_bytes()
    assert (len(b), sha(b)) == (r['bytes'], r['sha256']), str(p)
    assert not r.get('git_blob') or blob(b) == r['git_blob'], str(p)
    mode = r.get('native_mode')
    if isinstance(mode, str):
        mode = int(mode, 8)
    if mode is not None and 'mirror_path' not in r:
        assert stat.S_IMODE(s.st_mode) == mode, str(p)
    return b, {'read_path': str(p), 'read_mode': stat.S_IMODE(s.st_mode),
               'original_source_path': r['source_path']}

def main():
    independent_path = ROOT_REVIEW / 'independent-publication-inputs-v1.json'
    independent_body = independent_path.read_bytes()
    assert sha(independent_body) == 'a1586aad097e35c0ca6d49014fe82156964eb39d6201f4bb98b0c13bba0b9fe5'
    independent = json.loads(independent_body)
    assert len(independent['files']) == 131 and independent['prefix'] == PREFIX + 'independent-root/'
    author_path = HERE / 'author-publication-inputs-v1.json'
    author_body = author_path.read_bytes()
    assert sha(author_body) == '73c621841501906959d187416cf4e1470819e28d1d05f7d3ce0007fd389be282'
    author = json.loads(author_body)
    assert len(author['files']) == 46 and author['prefix'] == PREFIX + 'author/'
    freeze = json.loads((ROOT / 'candidate-freeze-v2.json').read_text())
    assert freeze['base_commit'] == BASE and freeze['base_tree'] == TREE
    parent = json.loads((ROOT_REVIEW / 'base-tree-v1.json').read_text())
    assert parent['sha'] == TREE and not parent['truncated']
    leaves = {r['path']: r for r in parent['tree'] if r['type'] != 'tree'}
    assert len(leaves) == 1739
    selected, inventory, sources, support, original_bodies = {}, [], [], [], {}

    def add(destination, mode, b, origin):
        assert destination not in selected and mode in ('100644', '100755'), destination
        assert destination.startswith(PREFIX) or destination in {'testpilot/history.py', 'testpilot/__main__.py', 'tests/test_history.py', 'docs/HISTORY.md', 'README.md'}, destination
        git = blob(b)
        selected[destination] = {'path': destination, 'mode': mode, 'sha': git,
                                 'encoding': 'base64', 'content': base64.b64encode(b).decode('ascii')}
        row = {'path': destination, 'mode': mode, 'bytes': len(b), 'sha256': sha(b)}
        inventory.append({**row, 'git_blob': git, 'origin': origin})
        if origin.get('read_path'):
            original_bodies[origin['read_path']] = b
        return row

    def add_row(r, destination):
        b, origin = capture(r)
        return add(destination, r['mode'], b, origin)

    for r in freeze['source_files']:
        r = {**r, 'native_mode': r['mode'], 'mode': '100755' if r['mode'] & 0o111 else '100644'}
        sources.append(add_row(r, r['path']))
    assert len(sources) == 5
    for r in author['files']:
        support.append(add_row(r, author['prefix'] + r['path']))
    explicit = [
        (HERE / 'README.md', 'README.md'),
        (HERE / 'owner-check-v1.json', 'owner-check-v1.json'),
        (author_path, 'author-publication-inputs-v1.json'),
        (independent_path, 'independent-publication-inputs-v1.json'),
        (HERE / 'seal-author-v1.py', 'seal-author-v1.py'),
        (Path(__file__), 'assemble-publication-v1.py'),
        (Path('/dev/shm/forge-d3745-testpilot-history-public-review.json'), 'peer-reviews/public-contract-review-v1.json'),
        (Path('/dev/shm/forge-d3745-testpilot-history-public-clarification-review.json'), 'peer-reviews/public-clarification-review-v1.json'),
    ]
    for p, dest in explicit:
        support.append(add_row(identity(p), PREFIX + dest))
    tool_authority = json.loads((TOOLS.parent / 'publication-tools.json').read_text())
    for r in tool_authority['files']:
        b = (TOOLS / r['path']).read_bytes()
        assert (len(b), sha(b), blob(b)) == (r['bytes'], r['sha256'], r['git_blob'])
    tools_record = {'schema': 'hamon.loom.testpilot-history.publication-tools.v1',
                    'repository': tool_authority['repository'], 'commit': tool_authority['commit'],
                    'files': tool_authority['files'], 'scope': 'Exact published maintained tools used read-only for selected layout and complete tree checks; no tool/product test replay.'}
    support.append(add(PREFIX + 'publication-tools.json', '100644', encode(tools_record), {'generated_from': 'Five exact maintained tool bodies and their previously authenticated immutable repository pin'}))
    binding = {'schema': 'hamon.loom.testpilot-history.source-binding.v1',
               'repository': 'Jacob-Met/testpilot', 'original_base': BASE, 'base_tree': TREE,
               'parent_leaf_count': len(leaves), 'workflow': {k: leaves['.github/workflows/ci.yml'][k] for k in ['path', 'sha', 'mode', 'size']},
               'source_files': freeze['source_files'], 'runtime_projection': freeze['runtime_projection'],
               'final_candidate_freeze': identity(ROOT / 'candidate-freeze-v2.json'),
               'author_descriptor': identity(author_path), 'independent_descriptor': identity(independent_path),
               'source_scope': 'Three new files and two additive existing files; all other current-parent leaves are preserved by full-tree admission.',
               'history': 'V1 author21+6 and five help pairs remain original. V2 changes only buffering=0 and has four focused controls. Independent34-command course consumes V2. No consumer dataset execution at publication preparation.'}
    support.append(add(PREFIX + 'source-binding-v1.json', '100644', encode(binding), {'generated_from': 'Exact final freeze, original parent and unchanged original descriptors'}))
    for r in independent['files']:
        add_row(r, independent['prefix'] + r['path'])
    for p, b in original_bodies.items():
        assert Path(p).read_bytes() == b, p
    packet = {'schema': 'hamon.source-packet/1', 'source': {'repository': 'Jacob-Met/testpilot', 'commit': BASE, 'tree': TREE}, 'files': [selected[k] for k in sorted(selected)]}
    policy = {'schema': 'hamon.publication-layout/1', 'source_files': sources, 'support_files': support,
              'evidence_prefix': PREFIX, 'descriptor_schema': independent['schema'], 'descriptor_prefix': independent['prefix']}
    out = HERE / 'admission-v1'
    out.mkdir()
    for n, b in [('source-packet.json', encode(packet)), ('layout-policy.json', encode(policy)),
                 ('selection-inventory.json', encode(inventory)), ('source-binding-v1.json', encode(binding)),
                 ('publication-tools.json', encode(tools_record)), ('original-independent-descriptor.json', independent_body)]:
        (out / n).open('xb').write(b)
    commands = []
    def run(label, argv):
        r = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        for stream in ['stdout', 'stderr']:
            (out / (label + '.' + stream)).open('xb').write(getattr(r, stream))
        commands.append({'label': label, 'argv': argv, 'exit_code': r.returncode,
                         'stdout': {'bytes': len(r.stdout), 'sha256': sha(r.stdout)},
                         'stderr': {'bytes': len(r.stderr), 'sha256': sha(r.stderr)}})
        assert r.returncode == 0, label + ': ' + r.stderr.decode(errors='replace')
    packet_path = out / 'source-packet.json'
    plan_path = out / 'git-object-plan.json'
    policy_path = out / 'layout-policy.json'
    run('prepare', [sys.executable, '-B', str(TOOLS / 'prepare_git_objects.py'), str(packet_path), '--sha256', sha(packet_path.read_bytes()), '--out', str(plan_path)])
    run('layout', [sys.executable, '-B', str(TOOLS / 'validate_publication_layout.py'), str(plan_path), '--sha256', sha(plan_path.read_bytes()), '--policy', str(policy_path), '--policy-sha256', sha(policy_path.read_bytes()), '--descriptor', str(independent_path), '--descriptor-sha256', sha(independent_body)])
    for p, b in original_bodies.items():
        assert Path(p).read_bytes() == b, p
    receipt = {'schema': 'hamon.loom.testpilot-history.publication-admission.v1', 'accepted': True,
               'source_files': len(sources), 'support_files': len(support), 'author_files': len(author['files']),
               'independent_files': len(independent['files']), 'selected_files': len(selected),
               'payload_bytes': sum(r['bytes'] for r in inventory), 'commands': commands,
               'plan': identity(plan_path), 'scope': 'Selected source/evidence admission only. No product execution or Git commit/ref mutation.'}
    (out / 'receipt.json').open('xb').write(encode(receipt))
    print(json.dumps(receipt, sort_keys=True))

if __name__ == '__main__':
    main()
