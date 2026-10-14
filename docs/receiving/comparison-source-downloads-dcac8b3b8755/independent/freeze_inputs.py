"""Author fictional saved inputs and exact source-download expectations before candidate."""
from pathlib import Path
import base64, copy, datetime, hashlib, json

ROOT = Path(__file__).resolve().parent
FIX = ROOT / 'fixtures'
FIX.mkdir(exist_ok=False)

def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()}

def report(role, files):
    cases = ([{'nodeid': 'repeat <case> Ω', 'outcome': 'failed', 'message': 'Literal failure <tag>\r\n', 'generated_file': '../removed Ω.py'},
              {'nodeid': 'repeat <case> Ω', 'outcome': 'passed', 'message': ''}]
             if role == 'before' else [{'nodeid': 'repeat <case> Ω', 'outcome': 'error', 'message': 'Literal error\n'}])
    target = {'path': 'src/literal Ω.py', 'qualname': 'same', 'source': 'def display_only():\n    return "Ω"\n',
              'lineno': 1, 'end_lineno': 2, 'changed_lines': [2]}
    return {'status': 'failed', 'changed_functions': [target, copy.deepcopy(target)] if role == 'before' else [target],
            'test_files': files, 'tests_written': len(files), 'repair_rounds_used': 0, 'max_repair_rounds': 1,
            'final': {'returncode': 1, 'timed_out': False, 'ok': False, 'duration_s': 0.25,
                      'output': 'Recorded output only\n', 'summary': role + ' retained summary',
                      'passed': 1 if role == 'before' else 0, 'failed': 1 if role == 'before' else 0,
                      'errors': 0 if role == 'before' else 1, 'skipped': 0, 'cases': cases,
                      'junit_available': False, 'coverage': None},
            'coverage': None, 'ledger': {'total_tokens': 0, 'total_cost_usd': 0, 'cost_is_complete': False,
                       'tokens_estimated': False, 'by_model': {}, 'entries': []},
            'rounds': [], 'plan': 'Fictional passive source only', 'message': role + ' fixture', 'patch': '',
            'unknown': {'preserve_spelling': 100.0, 'negative_zero': -0.0, 'text_id': '0007'}}

long_text = '  BEGIN\r\n\tΩ 中 😀\x00\x1b[31m <script>DISPLAY ONLY</script>\rbare\n' + '0123456789' * 80 + '\nTRAIL TWO  '
left = {'same.py': long_text, 'paired.py': '\n😀 café\n', 'empty.py': '',
        '../removed Ω.py': 'removed\r\n\tkeep spaces  ', 'lone-high.py': 'high \ud800 retained',
        'lone-low.py': 'valid before low\x00\n'}
right = {'lone-low.py': 'low \udfff retained', 'C:\\kept\\added.py': '\ufeffBOM is recorded\r\nΩ\t  ',
         'same.py': long_text + '\r\nAFTER\n', 'empty.py': '', 'paired.py': '\n😀 café\n',
         'lone-high.py': 'valid after high Ω\r\n'}
before, after = report('before', left), report('after', right)
empty_before, empty_after = report('before', {}), report('after', {})
empty_before['final'] = None
empty_after['final'] = None
bad_before, bad_after = copy.deepcopy(before), copy.deepcopy(after)
bad_before['test_files']['same.py'] = None
bad_after['test_files']['same.py'] = None

objects = {'before.json': before, 'after.json': after, 'empty-before.json': empty_before,
           'empty-after.json': empty_after, 'before-null.json': bad_before, 'after-null.json': bad_after}
fixture_pins = {}
for name, value in objects.items():
    text = json.dumps(value, ensure_ascii=True, indent=2).replace('100.0', '1e2') + '\n'
    if name == 'before.json':
        raw = b'\xef\xbb\xbf' + text.replace('\n', '\r\n').encode('ascii')
    else:
        raw = text.encode('ascii')
    (FIX / name).write_bytes(raw)
    fixture_pins[name] = identity(raw)

# This explicit ordering is an independent contract oracle, not renderer output.
order = ['../removed Ω.py', 'C:\\kept\\added.py', 'empty.py', 'lone-high.py', 'lone-low.py', 'paired.py', 'same.py']
assert order == sorted(set(left) | set(right))
files = []
for index, label in enumerate(order):
    row = {'index': index, 'path': label,
           'status': 'added' if label not in left else 'removed' if label not in right else 'unchanged' if left[label] == right[label] else 'changed'}
    for role, side in [('before', left), ('after', right)]:
        if label not in side:
            row[role] = {'state': 'absent'}
        else:
            value = side[label]
            try:
                raw = value.encode('utf-8', errors='strict')
            except UnicodeEncodeError:
                row[role] = {'state': 'unpaired', 'text': value}
            else:
                row[role] = {'state': 'download', 'text': value, 'filename': f'testpilot-{role}-file-{index}.txt',
                             'base64': base64.b64encode(raw).decode(), **identity(raw)}
    files.append(row)

criteria = {'schema': 'hamon.testpilot130.independent-criteria/1',
            'frozen_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'original_commit': '3441b6a2e708977ebfc75400d795501f357f656c',
            'original_tree': '6ad610e7b901d34298b4eff0c3c85f517d5b8df2',
            'original_packet': '431e88207343fc5ad1b78faabd6f6abfed7bf16e',
            'renderer': '0fd6c65058fd847342633a28fe6c8c8157b8cfc5',
            'reader': '11d8bbd4939b749760bd2b5fc26326a79ece1e40',
            'fixtures': fixture_pins, 'files': files,
            'cases': {'mixed': ['before.json', 'after.json'], 'empty': ['empty-before.json', 'empty-after.json']},
            'negative_cases': {'null-before': ['before-null.json', 'after.json'], 'null-after': ['before.json', 'after-null.json']},
            'selectors': {'file': '#file-{index}', 'link': 'a.generated-source-download', 'unavailable': 'p.generated-source-unavailable',
                          'attributes': ['data-file-index', 'data-role'], 'label': 'Download {Before|After} source'},
            'counts': {'mixed_files': 7, 'valid_source_downloads': 10, 'unpaired_notes': 2, 'absent_sides': 2,
                       'empty_payloads': 2, 'original_browser_downloads': 4, 'candidate_browser_downloads': 14},
            'contract': ['Strict decoded UTF-8 bytes, including literal leading FEFF, no added BOM or normalization.',
                         'Unchanged files retain both labeled roles; missing side has no link; unpaired surrogate has no lossy link.',
                         'Fixed sorted-union index filenames, not path-derived destination names.',
                         'Full original file table/diffs/source display and all other sections equal the original baseline.',
                         'Same initial disclosures and manual state after actions; native keyboard save; 390px document fit.',
                         'Print-media full source visibility, not physical print/PDF; no script, remote request, storage or source execution.',
                         'Original raw Before/After JSON downloaded exactly, including BOM/CRLF and numeric spelling.',
                         'Complete admitted inputs and observer bytes/stat conserved; managed cleanup recorded truthfully.'],
            'scope': 'Two fictional comparison pairs, four ordinary CLI cases, passive saved-page viewing and native downloads only. No test, model, provider, sandbox task, history discovery or repository mutation.'}
(ROOT / 'criteria.json').write_text(json.dumps(criteria, ensure_ascii=True, indent=2) + '\n')
print(json.dumps({'criteria': identity((ROOT/'criteria.json').read_bytes()), 'fixtures': fixture_pins,
                  'valid_downloads': sum(x[role]['state']=='download' for x in files for role in ['before','after'])}))
