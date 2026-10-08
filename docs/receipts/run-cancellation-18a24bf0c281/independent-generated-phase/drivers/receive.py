#!/usr/bin/env python3
"""Independent native caller/process-group receiving; production source is never edited."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path('/Users/me/testpilot-independent-interrupt-18a24bf0c281')
PYTHON = '/Users/me/capturesuite-independent-checkpoint-18a24bf0c281/venv/bin/python'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def identity(path):
    stat = path.stat()
    return {'bytes': stat.st_size, 'sha256': sha(path.read_bytes()),
            'inode': stat.st_ino, 'mode': stat.st_mode & 0o777,
            'mtime_ns': stat.st_mtime_ns}

def json_file(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def owned_ps(pids):
    pids = sorted({int(p) for p in pids if p})
    if not pids:
        return []
    result = subprocess.run(['/bin/ps', '-p', ','.join(str(p) for p in pids),
                             '-o', 'pid=,ppid=,pgid=,stat=,command='],
                            capture_output=True, text=True, timeout=3)
    rows = []
    for line in result.stdout.splitlines():
        fields = line.strip().split(None, 4)
        if len(fields) == 5:
            rows.append({'pid': int(fields[0]), 'ppid': int(fields[1]), 'pgid': int(fields[2]),
                         'stat': fields[3], 'command': fields[4], 'running': not fields[3].startswith('Z')})
    return rows

def source_state(label):
    manifest_path = ROOT / 'evidence' / ('source-intake.json' if label == 'baseline' else 'candidate-intake.json')
    manifest = json.loads(manifest_path.read_text())
    rows = []
    for entry in manifest['captured_files']:
        path = ROOT / ('source-' + label) / entry['path']
        data = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        rows.append({'path': entry['path'], 'git_blob': blob, 'sha256': sha(data),
                     'matches_frozen_source': blob == entry['git_blob'] and sha(data) == entry['sha256']})
    return rows

def fixture_state():
    return {str(path.relative_to(ROOT / 'fixture')): sha(path.read_bytes())
            for path in sorted((ROOT / 'fixture').rglob('*')) if path.is_file()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True, choices=('baseline', 'candidate'))
    args = parser.parse_args()
    label = args.label
    source = ROOT / ('source-' + label)
    run = ROOT / 'runs' / label
    if run.exists():
        raise SystemExit('Refusing to overwrite a previous receiving run')
    (run / 'control').mkdir(parents=True)
    (run / 'tmp').mkdir()
    output = run / 'saved-output'
    shutil.copytree(ROOT / 'fixture/previous-output', output)
    for i, path in enumerate(sorted(output.iterdir())):
        path.chmod(0o640 if i % 2 else 0o440)
        stamp = 1735689600000000000 + i * 1000000000
        os.utime(path, ns=(stamp, stamp))
    before_output = {p.name: identity(p) for p in sorted(output.iterdir())}
    before_source = source_state(label)
    before_fixture = fixture_state()
    expected = json.loads((ROOT / 'fixture/expected.json').read_text())
    freeze = json.loads((ROOT / 'evidence/driver-freeze.json').read_text())
    assert freeze['receiver_sha256'] == sha(Path(__file__).read_bytes())
    assert all(row['matches_frozen_source'] for row in before_source)
    assert before_fixture == freeze['fixture_state']
    checks = []
    report = {'label': label, 'source_before': before_source, 'fixture_before': before_fixture,
              'outputs_before': before_output, 'checks': checks,
              'receiver_sha256': freeze['receiver_sha256'],
              'started_utc': datetime.now(timezone.utc).isoformat()}
    def check(name, actual, target):
        checks.append({'name': name, 'passed': actual == target, 'actual': actual, 'expected': target})

    env = os.environ.copy()
    env.update(PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
               TP_REVIEW_CONTROL=str(run / 'control'), TMPDIR=str(run / 'tmp'))
    # The actual public CLI explicitly uses the existing offline backend.
    argv = [PYTHON, '-m', 'testpilot', 'run', '--repo', str(ROOT / 'fixture/project'),
            '--diff', str(ROOT / 'fixture/change.diff'), '--backend', 'scripted',
            '--script', str(ROOT / 'fixture/script'), '--rounds', '0', '--timeout', '30',
            '--python', PYTHON, '--out', str(output)]
    report['argv'] = argv
    report['cwd'] = str(source)
    report['environment_overrides'] = {k: env[k] for k in ['PYTHONPATH', 'PYTHONDONTWRITEBYTECODE',
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD', 'TP_REVIEW_CONTROL', 'TMPDIR']}
    cli = None
    owned_pids = []
    group = None
    group_proven = False
    generated = worker = None
    stdout_path, stderr_path = run / 'cli.stdout.txt', run / 'cli.stderr.txt'
    try:
        with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
            cli = subprocess.Popen(argv, cwd=source, env=env, stdout=stdout, stderr=stderr,
                                   stdin=subprocess.DEVNULL, start_new_session=True)
            report['cli_pid'] = cli.pid
            report['cli_pgid'] = os.getpgid(cli.pid)
            deadline = time.monotonic() + 12.0
            while time.monotonic() < deadline:
                generated = json_file(run / 'control/generated-ready.json')
                worker = json_file(run / 'control/worker-ready.json')
                heartbeat = json_file(run / 'control/heartbeat.json')
                if generated and worker and heartbeat:
                    break
                if cli.poll() is not None:
                    break
                time.sleep(.025)
            check('Actual generated verification is reached after existing tests and scripted model replies',
                  bool(generated and worker and heartbeat and cli.poll() is None), True)
            if not (generated and worker and heartbeat and cli.poll() is None):
                raise RuntimeError('Generated-phase fixture did not become ready; preserve this as an invalid receiving setup')
            report['generated_ready'] = generated
            report['worker_ready'] = worker
            report['heartbeat_before_signal'] = heartbeat
            check('The accepted generated file and its actual input assertion match the frozen reply',
                  [generated['generated_sha256'], generated['asserted_result'],
                   generated['phase'], generated['generated_path'].startswith(str(run / 'tmp'))],
                  [expected['generated_sha256'], 13, 'generated-verification', True])
            owned_pids = [generated['pid'], worker['pid']]
            group = generated['pgid']
            group_proven = (group == generated['pid'] and generated['ppid'] == cli.pid
                            and worker['ppid'] == generated['pid'] and worker['pgid'] == group
                            and generated['child_pid'] == worker['pid'] and group != os.getpgrp())
            check('Pytest owns a separate group and the recorded worker inherits that exact group', group_proven, True)
            if not group_proven:
                raise RuntimeError('Owned group identity was not established')
            report['owned_before_signal'] = owned_ps(owned_pids)
            check('Both owned processes are doing work before the cancellation signal',
                  sorted(row['pid'] for row in report['owned_before_signal'] if row['running']), sorted(owned_pids))
            check('No post-parent-exit marker exists before the parent exits',
                  (run / 'control/work-after-parent-exit.json').exists(), False)
            signal_time = time.monotonic()
            os.kill(cli.pid, signal.SIGINT)
            report['signal'] = {'number': int(signal.SIGINT), 'target_pid': cli.pid, 'monotonic': signal_time}
            try:
                cli.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                report['parent_exit_bound_exceeded'] = True
            elapsed = time.monotonic() - signal_time
            report['parent_exit'] = {'returncode': cli.poll(), 'duration_s': elapsed,
                                     'observed_monotonic': time.monotonic()}
            check('The CLI propagates cancellation and exits within the finite three-second bound',
                  bool(cli.poll() not in (None, 0) and elapsed < 3.0), True)
            report['owned_at_parent_exit'] = owned_ps(owned_pids)
            check('No owned pytest/worker process is still running when the CLI exits',
                  [row['pid'] for row in report['owned_at_parent_exit'] if row['running']], [])
            if cli.poll() is not None:
                pending = run / 'control/parent-exited.pending'
                write_json(pending, {'cli_pid': cli.pid, 'returncode': cli.returncode,
                                     'monotonic': report['parent_exit']['observed_monotonic']})
                pending.replace(run / 'control/parent-exited.json')
                # The flag is atomic and created strictly after observed parent exit.
                deadline = time.monotonic() + .65
                while time.monotonic() < deadline:
                    marker = json_file(run / 'control/work-after-parent-exit.json')
                    if marker is not None:
                        break
                    time.sleep(.025)
                marker = json_file(run / 'control/work-after-parent-exit.json')
                report['post_parent_exit_marker'] = marker
                check('The owned worker cannot continue after the post-parent-exit handshake', marker is None, True)
            else:
                check('The owned worker cannot continue after the post-parent-exit handshake', 'parent did not exit', True)
        check('Cancellation remains visible as KeyboardInterrupt and prints no publication success',
              ['KeyboardInterrupt' in stderr_path.read_text(), 'wrote ' in stdout_path.read_text()], [True, False])
    except Exception as exc:
        report['receiver_error'] = {'type': type(exc).__name__, 'message': str(exc)}
        check('Receiver setup and native flow complete without a harness error', False, True)
    finally:
        cleanup = {'owned_pids': owned_pids, 'pgid': group, 'actions': []}
        if group_proven:
            rows = owned_ps(owned_pids)
            cleanup['before'] = rows
            # Never signal a remembered group unless a still-owned live member proves it.
            live = [r for r in rows if r['running'] and r['pgid'] == group
                    and (str(run / 'tmp') in r['command'] or str(run / 'control') in r['command'])]
            if live:
                try:
                    os.killpg(group, signal.SIGKILL)
                    cleanup['actions'].append({'signal': 'SIGKILL', 'group': group,
                                               'live_owned_witness_pids': [r['pid'] for r in live]})
                except ProcessLookupError:
                    cleanup['actions'].append({'group': group, 'already_exited': True})
            deadline = time.monotonic() + 1.0
            while time.monotonic() < deadline and any(r['running'] for r in owned_ps(owned_pids)):
                time.sleep(.025)
            cleanup['after'] = owned_ps(owned_pids)
            check('All recorded owned work is stopped at the end of finite receiver cleanup',
                  [r['pid'] for r in cleanup['after'] if r['running']], [])
        if cli is not None and cli.poll() is None:
            cli.kill()
            cli.wait(timeout=2.0)
            cleanup['actions'].append({'signal': 'SIGKILL', 'owned_cli_pid': cli.pid})
        report['cleanup'] = cleanup
        after_output = {p.name: identity(p) for p in sorted(output.iterdir()) if p.is_file()}
        report['outputs_after'] = after_output
        check('All four preexisting output files preserve bytes/inode/mode/write time', after_output, before_output)
        check('No partial publication path is added to the existing output directory',
              sorted(p.name for p in output.iterdir()), sorted(before_output))
        after_fixture = fixture_state()
        check('Original project and scripted replies remain byte-identical', after_fixture, before_fixture)
        after_source = source_state(label)
        report['source_after'] = after_source
        check('All captured native production/context source bytes remain exact', after_source == before_source, True)
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        report['totals'] = {'checks': len(checks), 'passed': sum(c['passed'] for c in checks),
                            'failed': sum(not c['passed'] for c in checks), 'actual_cli_invocations': 1}
        write_json(run / 'report.json', report)
        print(json.dumps({'label': label, **report['totals'],
                          'failures': [c['name'] for c in checks if not c['passed']],
                          'parent_exit': report.get('parent_exit')}))
    return 0 if all(c['passed'] for c in checks) else 1

if __name__ == '__main__':
    raise SystemExit(main())
