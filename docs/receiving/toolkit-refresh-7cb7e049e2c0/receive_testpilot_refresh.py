"""Receive toolkit composition with real pytest and an actual full-device write error."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', required=True, type=Path)
    p.add_argument('--candidate', required=True, type=Path)
    p.add_argument('--python', required=True)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    pins = {label: {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                   for f in (root / 'testpilot').glob('*.py')}
            for label, root in [('baseline', args.baseline), ('candidate', args.candidate)]}
    assert pins['candidate']['recheck.py'] == '1b7d31f49cede49c45fe1fb0613b6e55fac292a7dece9b2645d1b55b141d95f6'
    assert pins['candidate']['__main__.py'] == 'e8a0516b1d8bb62df62ef64d829000414f6ccf48f4bd2641e5ebf422200be86f'
    for name, value in pins['baseline'].items():
        if name not in ('recheck.py', '__main__.py'):
            assert pins['candidate'][name] == value, name
    child = r'''
import os, pathlib, runpy
if os.environ.get('RECEIVE_INJECT_FULL') == '1':
    original = pathlib.Path.write_bytes
    def write(self, data):
        if self.name == 'recheck.json':
            with open('/dev/full', 'wb', buffering=0) as full:
                full.write(data)
            raise AssertionError('full device unexpectedly accepted output')
        return original(self, data)
    pathlib.Path.write_bytes = write
runpy.run_module('testpilot', run_name='__main__')
'''
    results = []
    with tempfile.TemporaryDirectory(prefix='testpilot-refresh-independent-', dir='/dev') as tmp:
        root = Path(tmp)
        for label, source in [('baseline', args.baseline), ('candidate', args.candidate)]:
            work = root / label
            project = work / 'project'
            project.mkdir(parents=True)
            (project / 'answer.py').write_text('def answer():\n    return 7\n')
            marker = work / 'native-test-completions'
            test = 'from answer import answer\nfrom pathlib import Path\ndef test_answer():\n    assert answer() == 7\n    with Path(' + repr(str(marker)) + ').open("a") as f:\n        f.write("native-pass\\n")\n'
            report = work / 'saved.json'
            report.write_text(json.dumps({'status': 'historical-only', 'test_files': {'tests/test_retained.py': test}}))
            original_report = report.read_bytes()
            project_before = {str(f.relative_to(project)): f.read_bytes() for f in project.rglob('*') if f.is_file()}
            out = work / 'final'
            env = os.environ.copy()
            env.update(PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(work),
                       TESTPILOT_BACKEND='unusable-backend', TESTPILOT_BASE_URL='http://127.0.0.1:1')
            argv = [args.python, '-B', '-c', child, 'recheck', '--repo', str(project),
                    '--report', str(report), '--out', str(out), '--python', args.python, '--timeout', '20']
            failed = subprocess.run(argv, env={**env, 'RECEIVE_INJECT_FULL': '1'}, capture_output=True, timeout=30)
            assert failed.returncode == 2, (label, failed.stdout, failed.stderr)
            assert b'No space left on device' in failed.stderr
            assert marker.read_text().splitlines() == ['native-pass']
            failure_destination_present = out.exists()
            failure_files = sorted(f.name for f in out.iterdir()) if out.exists() else []
            assert not list(work.glob('.testpilot-recheck-*'))
            retry = subprocess.run(argv, env={**env, 'RECEIVE_INJECT_FULL': '0'}, capture_output=True, timeout=30)
            if label == 'baseline':
                assert failure_destination_present and failure_files == ['recheck.md']
                assert retry.returncode == 2 and b'already exists' in retry.stderr
                assert marker.read_text().splitlines() == ['native-pass']
            else:
                assert not failure_destination_present and failure_files == []
                assert retry.returncode == 0, (retry.stdout, retry.stderr)
                assert marker.read_text().splitlines() == ['native-pass', 'native-pass']
                result = json.loads((out / 'recheck.json').read_bytes())
                assert result['model_calls'] == 0 and result['status'] == 'passed'
                assert result['final']['passed'] == 1 and result['final']['failed'] == 0
                assert result['source_report']['recorded_status'] == 'historical-only'
                assert result['source_report']['sha256'] == hashlib.sha256(original_report).hexdigest()
                assert result['test_files'] == {'tests/test_retained.py': test}
                for f in out.iterdir():
                    (args.out / f.name).write_bytes(f.read_bytes())
            assert report.read_bytes() == original_report
            assert project_before == {str(f.relative_to(project)): f.read_bytes() for f in project.rglob('*') if f.is_file()}
            version = subprocess.run([args.python, '-B', '-m', 'testpilot', '--version'], env=env,
                                     capture_output=True, timeout=10)
            if label == 'candidate':
                assert version.returncode == 0 and version.stdout == b'testpilot 0.1.0\n' and not version.stderr
            else:
                assert version.returncode == 2
            help_result = subprocess.run([args.python, '-B', '-m', 'testpilot', 'run', '--help'],
                                         env=env, capture_output=True, timeout=10)
            assert help_result.returncode == 0 and b'--progress' in help_result.stdout
            results.append({'label': label, 'fault_exit': failed.returncode,
                            'fault_stdout': failed.stdout.decode(), 'fault_stderr': failed.stderr.decode(),
                            'destination_after_fault': failure_destination_present,
                            'files_after_fault': failure_files, 'retry_exit': retry.returncode,
                            'retry_stdout': retry.stdout.decode(), 'retry_stderr': retry.stderr.decode(),
                            'native_completions': len(marker.read_text().splitlines()),
                            'version_exit': version.returncode, 'version_stdout': version.stdout.decode(),
                            'progress_help_available': True, 'source_report_and_project_unchanged': True})
    for label, root in [('baseline', args.baseline), ('candidate', args.candidate)]:
        assert pins[label] == {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in (root / 'testpilot').glob('*.py')}
    receipt = {'status': 'ACCEPT', 'source_pins': pins, 'cases': results,
               'source_unchanged': True, 'final_native_recheck_passed': 1, 'final_model_calls': 0,
               'fault': 'Actual /dev/full write injected only at report JSON write; native pytest and all other product execution unchanged.',
               'limits': 'Portable native CLI composition receiving. No new generation, installed adoption, Windows or post-publication move-failure guarantee.'}
    (args.out / 'receiving.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': 'ACCEPT', 'native_pytest_executions': 3,
                      'candidate_retry_exit': 0, 'candidate_version': '0.1.0', 'progress_available': True}))


if __name__ == '__main__':
    main()
