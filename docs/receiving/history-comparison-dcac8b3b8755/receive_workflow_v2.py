"""Receive a fictional history-to-comparison walkthrough; never execute report code."""
from pathlib import Path
from html.parser import HTMLParser
import base64, datetime, hashlib, json, os, subprocess, sys

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'testpilot125-current-integration/course/source'
ORIGINAL = ROOT / 'course/saved-runs'
COURSE = ROOT / 'workflow-v2'

def ident(p):
    b = p.read_bytes(); s = p.stat()
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest(),
            'mode': str(s.st_mode), 'mtime_ns': str(s.st_mtime_ns), 'inode': str(s.st_ino)}

def inventory(root):
    return {p.relative_to(root).as_posix(): ident(p) for p in sorted(root.rglob('*')) if p.is_file()}

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.ids = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs: self.ids.append(attrs['id'])
        if tag == 'a': self.links.append(attrs)

assert sys.version_info[:3] == (3, 12, 14)
expected_source = json.loads((ROOT.parent / 'testpilot125-publication/SOURCE.json').read_text())['current_main_composition']['runtime']
for row in expected_source:
    assert ident(SOURCE / row['path'])['git_blob'] == row['git_blob'], row['path']
assert len(inventory(SOURCE)) == 16
COURSE.mkdir()
saved = COURSE / 'saved-runs'; saved.mkdir()
derivation = {}
for role in ('before', 'after'):
    original = ORIGINAL / role / 'report.json'
    data = json.loads(original.read_bytes().decode('utf-8-sig'))
    assert 'coverage' not in data['final']
    data['final']['coverage'] = None
    target = saved / role; target.mkdir()
    output = target / 'report.json'
    output.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    check = json.loads(output.read_bytes()); del check['final']['coverage']
    assert check == json.loads(original.read_bytes().decode('utf-8-sig'))
    derivation[role] = {'original': ident(original), 'example': ident(output),
                        'semantic_change': 'Add final.coverage:null; reserialize UTF-8/LF. This is a new fictional fixture, not the accepted original bytes.'}
watched = [Path(__file__).resolve(), ROOT / 'course/receiving.json', ROOT / 'course/history.stdout.json']
record = {'schema': 'testpilot.saved-review-walkthrough/1', 'started': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'source_commit': '83c43077b7fcb168de43e15274f6e8f1f6b37d3c',
          'source_scope': 'Exact 16-module ordinary CLI closure joined to adopted source; no product change.',
          'python': sys.version, 'derivation': derivation, 'passed': False, 'commands': [], 'checks': [],
          'source_before': inventory(SOURCE), 'inputs_before': inventory(saved), 'original_before': inventory(ROOT / 'course'),
          'witness_before': {str(p): ident(p) for p in watched}}

def check(name, actual, expected):
    record['checks'].append({'name': name, 'actual': actual, 'expected': expected, 'passed': actual == expected})
    assert actual == expected, name

def run(label, args):
    argv = [sys.executable, '-B', '-m', 'testpilot', *args]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1'); env.pop('PYTHONPATH', None)
    child = subprocess.Popen(argv, cwd=SOURCE, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try: out, err = child.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        child.kill(); out, err = child.communicate(); raise
    (COURSE / (label + '.stdout')).write_bytes(out); (COURSE / (label + '.stderr')).write_bytes(err)
    record['commands'].append({'label': label, 'argv': argv, 'pid': child.pid, 'exit': child.returncode})
    check(label + ' exit', child.returncode, 0); check(label + ' stderr empty', err == b'', True)
    return out

try:
    result = json.loads(run('history', ['history', '--root', str(saved), '--kind', 'generation', '--max-depth', '1', '--json']))
    check('history complete', result['complete'], True)
    check('history problems', result['problems'], [])
    check('history two generation rows', [(v['path'], v['kind']) for v in result['runs']],
          [('after/report.json', 'generation'), ('before/report.json', 'generation')])
    check('history hashes match selected paths', {v['path']: v['sha256'] for v in result['runs']},
          {role + '/report.json': ident(saved / role / 'report.json')['sha256'] for role in ('before', 'after')})
    output = COURSE / 'comparison.html'
    run('compare', ['compare', '--before', str(saved / 'before/report.json'), '--after', str(saved / 'after/report.json'), '--out', str(output)])
    parsed = Links(); parsed.feed(output.read_text())
    index = [v['href'] for v in parsed.links if v.get('href', '').startswith('#diagnostic-')]
    expected = ['#diagnostic-before-case-2', '#diagnostic-before-case-4', '#diagnostic-before-case-6',
                '#diagnostic-after-case-1', '#diagnostic-after-case-2', '#diagnostic-after-case-5']
    check('six retained occurrence links', index, expected)
    check('each target unique', [parsed.ids.count(v[1:]) for v in expected], [1] * 6)
    downloads = [v for v in parsed.links if v.get('download')]
    check('two original report download links', len(downloads), 2)
    for role, link in zip(('before', 'after'), downloads):
        prefix, encoded = link['href'].split(',', 1)
        check(role + ' base64 data URL', prefix.endswith(';base64'), True)
        check(role + ' embedded exact derivative input', base64.b64decode(encoded, validate=True) == (saved / role / 'report.json').read_bytes(), True)
    record['output'] = ident(output); record['passed'] = True
except Exception as exc:
    record['error'] = type(exc).__name__ + ': ' + str(exc)
finally:
    record['source_after'] = inventory(SOURCE); record['inputs_after'] = inventory(saved)
    record['original_after'] = inventory(ROOT / 'course'); record['witness_after'] = {str(p): ident(p) for p in watched}
    for label in ('source', 'inputs', 'original', 'witness'):
        same = record[label + '_before'] == record[label + '_after']
        record[label + '_preserved'] = same; record['passed'] = record['passed'] and same
    record['finished'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (COURSE / 'receiving.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'passed': record['passed'], 'checks': len(record['checks']), 'commands': record['commands'],
                      'error': record.get('error'), 'receipt': ident(COURSE / 'receiving.json')}))
raise SystemExit(0 if record['passed'] else 1)
