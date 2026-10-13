"""Public-contract-only TestPilot fixture and exact-output preparation.

No product imports, scanner traversal, subprocesses or candidate source reads.
Every expected membership/count/problem list below is explicitly authored.
"""
import copy
import hashlib
import json
import os
import stat
from pathlib import Path

BASE = Path('/workspace/scratch/d3745ea0f44f')
OUT = BASE / 'root-testpilot-history/oracles'
ORIGINAL = BASE / 'loom-testpilot-history/original/eval/results'
PREP = BASE / 'loom-testpilot-history/preparation'
NOTICE = 'Saved records only. Reported outcomes are historical; no tests or model calls were run. Results are complete only within the selected root, depth and stated budgets; paths are not chronology.'
LIMITS = {'candidate_files': 1000, 'directory_entries': 20000, 'report_bytes': 16777216, 'total_bytes': 67108864}
MESSAGES = {'candidate_limit': 'Candidate-file budget reached.', 'entry_limit': 'Directory-entry budget reached.', 'total_bytes_limit': 'Total report-byte budget reached.', 'report_bytes_limit': 'Report exceeds the per-file byte limit.', 'read_error': 'Could not read a complete regular report.', 'unsupported_schema': 'Unsupported saved-report schema.', 'invalid_json': 'Not supported finite UTF-8 JSON.', 'invalid_report': 'Not a supported generation or recheck core record.'}
FILES, DIRS, ROOTS, CASES = [], [], [], []


def dump(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def mkdir(p):
    if not p.exists():
        p.mkdir(parents=True)
    for q in [p, *p.parents]:
        if q == OUT or OUT in q.parents:
            if str(q) not in DIRS:
                DIRS.append(str(q))
    return p


def root(name):
    p = mkdir(OUT / 'inputs' / name)
    ROOTS.append(str(p))
    return p


def put(p, raw, provenance='explicitly authored synthetic fixture'):
    mkdir(p.parent)
    with p.open('xb') as f:
        f.write(raw)
    p.chmod(0o644)
    FILES.append({'path': str(p), 'kind': 'regular', 'bytes': len(raw), 'sha256': sha(raw), 'mode': 0o644, 'provenance': provenance})
    return raw


def hardlink(p, source, raw):
    mkdir(p.parent)
    os.link(source, p)
    FILES.append({'path': str(p), 'kind': 'regular', 'bytes': len(raw), 'sha256': sha(raw), 'mode': 0o644, 'hardlink_to': str(source), 'provenance': 'explicit synthetic hard-linked candidate, separate path remains separate record'})


def link(p, target):
    mkdir(p.parent)
    p.symlink_to(target)
    FILES.append({'path': str(p), 'kind': 'symlink', 'target': str(target), 'mode': 0o777})


def problem(path, code):
    return {'path': path, 'code': code, 'message': MESSAGES[code]}


def recorded_final(summary, rc, passed, failed, errors=0, skipped=0, junit=None):
    return {'summary': summary, 'returncode': rc, 'timed_out': False, 'passed': passed, 'failed': failed, 'errors': errors, 'skipped': skipped, 'junit_available': junit}


def row(path, raw, *, kind='generation', status='passed', targets=(), tests=(), final=None, context=None):
    return {'path': path, 'kind': kind, 'bytes': len(raw), 'sha256': sha(raw), 'status': status, 'targets': list(targets), 'test_paths': sorted(tests), 'final': final, 'recheck_context': context}


def result(p, *, depth=1, statuses=(), query=None, kind=None, entries, candidates, read_bytes, admitted, runs=(), problems=()):
    runs = sorted(runs, key=lambda r: r['path'])
    problems = sorted(problems, key=lambda r: (r['path'], r['code']))
    return {'schema': 'testpilot.history/1', 'root': str(p.resolve()), 'max_depth': depth, 'filters': {'statuses': list(statuses), 'query': query, 'kind': kind}, 'complete': not problems, 'limits': LIMITS, 'counts': {'entries_seen': entries, 'candidate_files': candidates, 'bytes_read': read_bytes, 'admitted': admitted, 'matched': len(runs), 'problems': len(problems)}, 'runs': runs, 'problems': problems, 'notice': NOTICE}


def text(value):
    compact = lambda x: json.dumps(x, ensure_ascii=True, sort_keys=True)
    lines = ['TestPilot saved-run history', 'Root: ' + compact(value['root']), 'Complete within selected scope: ' + str(value['complete']).lower(), 'Counts: ' + compact(value['counts']), 'Filters: ' + compact(value['filters'])]
    for r in value['runs']:
        lines += ['Run: ' + compact(r['path']) + ' | ' + r['kind'] + ' | ' + compact(r['status']) + ' | ' + str(r['bytes']) + ' bytes | SHA256 ' + r['sha256'], '  Targets: ' + compact(r['targets']), '  Retained test paths: ' + compact(r['test_paths']), '  Recorded final: ' + compact(r['final']), '  Recheck context: ' + compact(r['recheck_context'])]
    for r in value['problems']:
        lines.append('Problem: ' + compact(r['path']) + ' [' + r['code'] + '] ' + r['message'])
    lines.append(NOTICE)
    return ('\n'.join(lines) + '\n').encode()


def case(name, p, value, *, options=(), text_mode=False):
    expected = text(value) if text_mode else dump(value)
    path = OUT / 'expected' / (name + '.stdout')
    with path.open('xb') as f:
        f.write(expected)
    CASES.append({'name': name, 'args': ['history', '--root', str(p), *options, *([] if text_mode else ['--json'])], 'expected_exit': 0 if value['complete'] else 1, 'expected_stdout_path': str(path), 'expected_stdout_bytes': len(expected), 'expected_stdout_sha256': sha(expected), 'expected_stderr': '', 'oracle': 'Explicit public-contract row/count/problem membership; only byte lengths and hashes computed from prepared input bytes.'})


def invalid(name, argv, contains):
    p = OUT / 'expected' / (name + '.stdout')
    p.write_bytes(b'')
    CASES.append({'name': name, 'args': argv, 'expected_exit': 2, 'expected_stdout_path': str(p), 'expected_stdout_bytes': 0, 'expected_stdout_sha256': sha(b''), 'expected_stderr': None, 'stderr_contains': contains, 'oracle': 'Bounded invalid-option/root prefix; exact OS/argparse prose is not invented.'})


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    mkdir(OUT / 'expected')
    seeds = mkdir(OUT / 'seeds')
    raw_real = {}
    real_pins = {'calc_clamp': '00ce7170150b268cf7484de03658cb4af8f61bcdd64f1500dee46dfe004d52ac', 'stats_median': '42d085ec5c1d204a85684fd4677bf7cf421ca5c1a090a1f95a51f43ff58bc9d0'}
    for name, expected in real_pins.items():
        raw = (ORIGINAL / name / 'report.json').read_bytes()
        assert sha(raw) == expected
        raw_real[name] = raw
        put(seeds / (name + '.json'), raw, 'Exact producer-retained generation report at f9ba2d2260f7aa93b3958661aa178ad418df9af6; root independently fetched Git body')
    core = {'schema': None, 'status': 'no_changes', 'changed_functions': [], 'repair_rounds_used': 0, 'max_repair_rounds': 0, 'test_files': {}, 'tests_written': 0, 'final': None, 'patch': '', 'coverage': None, 'ledger': {}, 'rounds': [], 'plan': '', 'message': ''}
    simple = dump(core)
    put(seeds / 'synthetic-minimal.json', simple)
    unicode_core = copy.deepcopy(core)
    unicode_core.update(status='model_error', changed_functions=[{'path': 'Src/Σ[bar].py', 'qualname': 'Straße.handle', 'source': 'PRIVATE_SOURCE_ONLY_Ω', 'lineno': 1, 'end_lineno': 1, 'changed_lines': [1]}, {'path': 'Src/Σ[bar].py', 'qualname': 'Straße.handle', 'source': 'second source body', 'lineno': 1, 'end_lineno': 1, 'changed_lines': []}], test_files={'tests/test_東京[1].py': 'PRIVATE_TEST_BODY', 'tests/a.py': '# authored only'}, tests_written=2, message='PRIVATE_MESSAGE_ONLY')
    unicode_raw = dump(unicode_core)
    put(seeds / 'synthetic-unicode.json', unicode_raw)
    final_core = {'returncode': 1, 'timed_out': False, 'ok': False, 'duration_s': 0.5, 'output': 'OUTPUT_BODY_ONLY', 'summary': 'literal saved failure', 'passed': 1, 'failed': 2, 'errors': 0, 'skipped': 3, 'cases': [], 'coverage': None, 'junit_available': False, 'timeout_s': None, 'generated_files': [], 'generated': None}
    source_report = {'path': '/UNOPENED/SOURCE_REPORT_ONLY', 'sha256': 'literal-hash-not-authenticated', 'recorded_status': None}
    context = {'repo': '/UNOPENED/REPO', 'python': '/UNOPENED/PYTHON', 'started_at': 'not-a-date-z', 'finished_at': 'not-a-date-a', 'source_report': source_report}
    recheck = {'schema': 'testpilot.recheck/1', 'status': 'failed', 'ok': False, **context, 'test_files': {'tests/test_東京[1].py': 'not executed', 'tests/a.py': 'not opened'}, 'retained_tests': [{'path': 'tests/test_東京[1].py', 'sha256': 'saved-hash', 'placement': 'authored', 'bytes': 0}], 'final': final_core, 'model_calls': 0, 'scope': 'Explicitly synthetic saved recheck, not execution evidence'}
    recheck_raw = dump(recheck)
    put(seeds / 'synthetic-recheck.json', recheck_raw)

    mixed = root('mixed')
    put(mixed / 'report.json', raw_real['calc_clamp'], 'Exact retained calc_clamp report')
    put(mixed / 'alpha/report.json', raw_real['stats_median'], 'Exact retained stats_median report')
    put(mixed / 'beta/recheck.json', recheck_raw)
    put(mixed / 'γ[Case]/recheck.json', unicode_raw)
    put(mixed / 'deep/nested/report.json', simple)
    put(mixed / 'ignore.txt', b'not a candidate\n')
    calc = row('report.json', raw_real['calc_clamp'], status='suspected_code_bug', targets=[{'path': 'calc.py', 'qualname': 'clamp'}], tests=['tests/test_calc_clamp.py'], final=recorded_final('3 passed, 3 failed, 0 errors, 0 skipped (rc=1)', 1, 3, 3))
    median = row('alpha/report.json', raw_real['stats_median'], targets=[{'path': 'stats.py', 'qualname': 'median'}], tests=['tests/test_median.py'], final=recorded_final('4 passed, 0 failed, 0 errors, 0 skipped (rc=0)', 0, 4, 0))
    rr = row('beta/recheck.json', recheck_raw, kind='recheck', status='failed', tests=['tests/test_東京[1].py', 'tests/a.py'], final=recorded_final('literal saved failure', 1, 1, 2, skipped=3, junit=False), context=context)
    ur = row('γ[Case]/recheck.json', unicode_raw, status='model_error', targets=[{'path': 'Src/Σ[bar].py', 'qualname': 'Straße.handle'}] * 2, tests=['tests/test_東京[1].py', 'tests/a.py'])
    deep = row('deep/nested/report.json', simple, status='no_changes')
    base_runs = [calc, median, rr, ur]
    size = sum(r['bytes'] for r in base_runs)
    def mixed_result(runs=base_runs, **kw):
        return result(mixed, entries=10, candidates=4, read_bytes=size, admitted=4, runs=runs, **kw)
    case('mixed-default-json', mixed, mixed_result())
    case('mixed-default-text', mixed, mixed_result(), text_mode=True)
    case('mixed-root-only', mixed, result(mixed, depth=0, entries=6, candidates=1, read_bytes=calc['bytes'], admitted=1, runs=[calc]), options=['--max-depth', '0'])
    case('mixed-depth-two', mixed, result(mixed, depth=2, entries=11, candidates=5, read_bytes=size+len(simple), admitted=5, runs=base_runs+[deep]), options=['--max-depth', '2'])
    statuses = ['failed', 'passed', 'failed']
    case('statuses-or-kind-query-and', mixed, mixed_result([rr], statuses=statuses, kind='recheck', query='[1]'), options=['--status','failed','--status','passed','--status','failed','--kind','recheck','--query','[1]'])
    case('literal-casefold-source-path', mixed, mixed_result([ur], query='src/ς[BAR].PY'), options=['--query','src/ς[BAR].PY'])
    case('literal-casefold-qualname', mixed, mixed_result([ur], query='STRASSE'), options=['--query','STRASSE'])
    case('literal-relative-path', mixed, mixed_result([ur], query='Γ[case]'), options=['--query','Γ[case]'])
    case('literal-test-path', mixed, mixed_result([rr,ur], query='東京[1]'), options=['--query','東京[1]'])
    for name, query in [('source-body-not-searched','PRIVATE_SOURCE_ONLY_Ω'),('recorded-source-path-not-searched','SOURCE_REPORT_ONLY'),('diagnostic-body-not-searched','OUTPUT_BODY_ONLY'),('status-not-searched','suspected_code_bug')]:
        case(name, mixed, mixed_result([], query=query), options=['--query',query])
    case('empty-query', mixed, mixed_result(query=''), options=['--query',''])
    case('unknown-empty-status', mixed, mixed_result([], statuses=['','unknown']), options=['--status','','--status','unknown'])
    empty = root('empty')
    case('empty-root', empty, result(empty, entries=0,candidates=0,read_bytes=0,admitted=0))

    malformed = root('malformed')
    badbool = copy.deepcopy(core); badbool['tests_written'] = True
    data = {'a-good/report.json': simple, 'b-bom/recheck.json': b'\xef\xbb\xbf'+simple, 'c-json/report.json': b'{', 'd-schema/report.json': b'{"schema":"future/1"}', 'e-duplicate/report.json': b'{"schema":null,"schema":null}', 'f-nonfinite/report.json': b'{"x":NaN}', 'g-overflow/report.json': b'{"x":1e400}', 'h-core-bool/report.json': dump(badbool), 'i-nonobject/report.json': b'[]', 'j-utf8/report.json': b'\xff'}
    for path, raw in data.items(): put(malformed/path,raw)
    problems = [problem(p,'unsupported_schema' if p.startswith('d-') else 'invalid_report' if p.startswith(('h-','i-')) else 'invalid_json') for p in list(data)[2:]]
    filtered = result(malformed,statuses=['passed'],entries=20,candidates=10,read_bytes=sum(map(len,data.values())),admitted=2,runs=[],problems=problems)
    case('invalid-neighbors-survive-filter',malformed,filtered,options=['--status','passed'])
    case('invalid-neighbor-text',malformed,filtered,options=['--status','passed'],text_mode=True)

    links = root('internal-links')
    put(links/'report.json',simple)
    mkdir(links/'report.json.dir')
    mkdir(links/'recheck.json')
    link(links/'symlink-dir',mixed)
    link(links/'linked/report.json',seeds/'calc_clamp.json')
    link(links/'linked/recheck.json',seeds/'synthetic-recheck.json')
    case('internal-symlinks-and-candidate-named-directory',links,result(links,entries=7,candidates=1,read_bytes=len(simple),admitted=1,runs=[row('report.json',simple,status='no_changes')]))
    selected_link=OUT/'inputs'/'selected-root-link';link(selected_link,mixed)
    case('explicit-root-symlink-resolves',selected_link,mixed_result())
    fifo=root('named-fifo');os.mkfifo(fifo/'report.json',0o600)
    FILES.append({'path':str(fifo/'report.json'),'kind':'fifo','mode':0o600,'body_read_expected':False})
    put(fifo/'safe/recheck.json',simple)
    case('named-fifo-no-read',fifo,result(fifo,entries=3,candidates=2,read_bytes=len(simple),admitted=1,runs=[row('safe/recheck.json',simple,status='no_changes')],problems=[problem('report.json','read_error')]))
    hard=root('hardlinked-records');put(hard/'report.json',simple);hardlink(hard/'recheck.json',hard/'report.json',simple)
    case('hardlinks-distinct-records',hard,result(hard,entries=2,candidates=2,read_bytes=2*len(simple),admitted=2,runs=[row('report.json',simple,status='no_changes'),row('recheck.json',simple,status='no_changes')]))

    cap=root('candidate-budget')
    for n in range(1001): hardlink(cap/f'd{n:04d}'/'report.json',seeds/'synthetic-minimal.json',simple)
    case('actual-1001-candidate-limit',cap,result(cap,statuses=['unknown'],entries=2002,candidates=1000,read_bytes=1000*len(simple),admitted=1000,problems=[problem('d1000/report.json','candidate_limit')]),options=['--status','unknown'])
    entries=root('entry-budget')
    for n in range(20000): put(entries/f'ignored-{n:05d}',b'', 'Explicit ignored entry, not report body')
    put(entries/'report.json',simple)
    case('actual-20001-entry-limit',entries,result(entries,entries=20000,candidates=0,read_bytes=0,admitted=0,problems=[problem('.','entry_limit')]))

    exact = simple+b' '*(LIMITS['report_bytes']-len(simple))
    over = exact+b' '
    put(seeds/'exact-16MiB.json',exact,'Synthetic valid core followed by JSON whitespace; exactly16MiB')
    put(seeds/'oversize-16MiB-plus1.json',over,'Synthetic regular file exceeding16MiB by one byte')
    boundary=root('exact-report-boundary');hardlink(boundary/'report.json',seeds/'exact-16MiB.json',exact)
    case('exact-16MiB-admitted',boundary,result(boundary,entries=1,candidates=1,read_bytes=len(exact),admitted=1,runs=[row('report.json',exact,status='no_changes')]))
    oversized=root('oversize-healthy-sibling');hardlink(oversized/'a/report.json',seeds/'oversize-16MiB-plus1.json',over);put(oversized/'b/report.json',simple)
    case('per-file-oversize-continues',oversized,result(oversized,entries=4,candidates=2,read_bytes=len(simple),admitted=1,runs=[row('b/report.json',simple,status='no_changes')],problems=[problem('a/report.json','report_bytes_limit')]))
    total=root('total-budget')
    for name in 'abcde': hardlink(total/name/'report.json',seeds/'exact-16MiB.json',exact)
    total_runs=[row(n+'/report.json',exact,status='no_changes') for n in 'abcd']
    case('64MiB-exact-then-fifth-counted',total,result(total,entries=10,candidates=5,read_bytes=LIMITS['total_bytes'],admitted=4,runs=total_runs,problems=[problem('e/report.json','total_bytes_limit')]))
    exact_total=root('exact-total-boundary')
    for name in 'abcd': hardlink(exact_total/name/'report.json',seeds/'exact-16MiB.json',exact)
    case('exact-64MiB-complete',exact_total,result(exact_total,entries=8,candidates=4,read_bytes=LIMITS['total_bytes'],admitted=4,runs=total_runs))
    precedence=root('per-file-before-global')
    for name in 'abcd': hardlink(precedence/name/'report.json',seeds/'exact-16MiB.json',exact)
    hardlink(precedence/'e/report.json',seeds/'oversize-16MiB-plus1.json',over);put(precedence/'f/report.json',simple)
    case('per-file-precedes-global-budget',precedence,result(precedence,entries=12,candidates=6,read_bytes=LIMITS['total_bytes'],admitted=4,runs=total_runs,problems=[problem('e/report.json','report_bytes_limit'),problem('f/report.json','total_bytes_limit')]))
    invalid('missing-root',['history','--root',str(OUT/'inputs'/'absent'),'--json'],'testpilot: cannot scan saved runs:')
    invalid('file-root',['history','--root',str(seeds/'synthetic-minimal.json'),'--json'],'testpilot: cannot scan saved runs:')
    invalid('invalid-depth',['history','--root',str(empty),'--max-depth','9','--json'],'testpilot: cannot scan saved runs:')
    invalid('argparse-invalid-kind',['history','--root',str(empty),'--kind','other'],'invalid choice')
    invalid('argparse-missing-root',['history','--json'],'--root')

    spec={'schema':'hamon.anvil.testpilot-history.case-spec.v1','cases':CASES,'input_roots':ROOTS,'files':FILES,'directories':sorted(DIRS),'source_scope':'Candidate not read or imported. Only public contract/addendum and two pinned retained reports used. Counts/membership/problems explicitly authored, not obtained from a scanner.','budget_cleanup':'Only after receiving, owner may retire explicitly listed disposable input roots and seed budget files while preserving this generator, complete metadata, exact outputs and executed receipt.'}
    (OUT/'case-spec-v1.json').write_bytes(dump(spec))
    provenance={'schema':'hamon.anvil.testpilot-history.oracle-provenance.v1','preparation_only':True,'candidate_source_read':False,'product_execution':False,'source_reports':[{'path':str(ORIGINAL/n/'report.json'),'sha256':v} for n,v in real_pins.items()],'public_inputs':[{'path':str(PREP/n),'bytes':len((PREP/n).read_bytes()),'sha256':sha((PREP/n).read_bytes())} for n in ['public-contract-v1.md','public-contract-v1-addendum.json']],'generator':{'path':str(Path(__file__).resolve()),'bytes':len(Path(__file__).read_bytes()),'sha256':sha(Path(__file__).read_bytes())},'case_spec':{'path':str(OUT/'case-spec-v1.json'),'bytes':len((OUT/'case-spec-v1.json').read_bytes()),'sha256':sha((OUT/'case-spec-v1.json').read_bytes())},'case_count':len(CASES),'file_records':len(FILES),'arithmetic_notes':['Mixed depth0 sees6entries/1candidate; depth1 sees10entries/4candidates; depth2 sees11entries/5candidates.','Candidate limit admits1000candidate bodies; all1001root directory names plus1001child report entries yield2002entries before refusing overflow candidate.','Entry overflow refuses the entire20001-entry root list; no candidate body is processed.','Total-byte overflow candidate is included in candidate_files per681-byte accepted addendum.','JSON byte padding is allowed trailing whitespace, so exact16MiB core does not fabricate a huge displayed field.','No case infers timestamp chronology, executes recorded paths or validates authenticity of recorded hashes.']}
    (OUT/'provenance-v1.json').write_bytes(dump(provenance))
    print(json.dumps({'accepted_preparation':True,'cases':len(CASES),'file_records':len(FILES),'case_spec':provenance['case_spec'],'generator':provenance['generator']}))


if __name__ == '__main__':
    main()
