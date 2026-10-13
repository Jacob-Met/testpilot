"""Receive live notices while an actual native pytest case is still waiting."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


@pytest.mark.parametrize('mode', ['quiet', 'progress', 'broken_stderr'])
def test_real_scripted_cli_progress_arrives_before_native_release(tmp_path, mode):
    project = tmp_path / 'project'
    project.mkdir()
    (project / 'pytest.ini').write_text('[pytest]\n')
    (project / 'calc.py').write_text('def double(value):\n    return value * 2\n')
    barrier, release = tmp_path / 'entered', tmp_path / 'release'
    (project / 'test_existing.py').write_text(
        'from pathlib import Path\nimport time\nfrom calc import double\n\n'
        'def test_existing():\n'
        f'    Path({str(barrier)!r}).write_text("entered")\n'
        '    deadline = time.monotonic() + 10\n'
        f'    while not Path({str(release)!r}).exists():\n'
        '        assert time.monotonic() < deadline, "receiver did not release test"\n'
        '        time.sleep(.01)\n'
        '    assert double(21) == 42\n'
    )
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in project.iterdir()}
    diff = tmp_path / 'change.diff'
    diff.write_text('--- /dev/null\n+++ b/calc.py\n@@ -0,0 +1,2 @@\n'
                    '+def double(value):\n+    return value * 2\n')
    responses = tmp_path / 'responses'
    responses.mkdir()
    (responses / '01.txt').write_text('Exercise the doubled value.')
    for name, expected in [('02.txt', 99), ('03.txt', 42)]:
        (responses / name).write_text(
            '```python path=tests/test_generated.py\nfrom calc import double\n\n'
            f'def test_double():\n    assert double(21) == {expected}\n```\n')
    out = tmp_path / 'result'
    command = [sys.executable, '-B', '-m', 'testpilot', 'run', '--repo', str(project),
               '--diff', str(diff), '--backend', 'scripted', '--script', str(responses),
               '--no-coverage', '--timeout', '5', '--rounds', '1', '--out', str(out)]
    if mode != 'quiet':
        command.append('--progress')
    environment = os.environ.copy()
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    environment['PYTHONPATH'] = str(Path(__file__).resolve().parents[1])
    for key in list(environment):
        if key.startswith('TESTPILOT_'):
            environment.pop(key)
    error_path = tmp_path / 'stderr.txt'
    if mode == 'broken_stderr':
        read_fd, write_fd = os.pipe()
        os.close(read_fd)
        sink = os.fdopen(write_fd, 'w')
    else:
        sink = error_path.open('w')
    with sink:
        child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=sink, text=True,
                                 cwd=tmp_path, env=environment)
        try:
            deadline = time.monotonic() + 8
            while not barrier.exists():
                assert child.poll() is None, 'CLI exited before the native fixture entered'
                assert time.monotonic() < deadline, 'native fixture did not enter'
                time.sleep(.01)
            assert child.poll() is None
            assert not out.exists(), 'final output must still be pending'
            if mode == 'progress':
                assert error_path.read_text() == '[testpilot] Baseline pytest: running\n'
            elif mode == 'quiet':
                assert error_path.read_text() == ''
            release.write_text('continue')
            stdout, _ = child.communicate(timeout=10)
        finally:
            release.write_text('continue')
            if child.poll() is None:
                child.kill()
                child.communicate()
    assert child.returncode == 0, stdout
    report = json.loads((out / 'report.json').read_text())
    assert report['status'] == 'passed'
    assert report['repair_rounds_used'] == 1
    assert report['final']['junit_available']
    assert sum(case['outcome'] == 'passed' for case in report['final']['cases']) == 2
    assert '[testpilot]' not in stdout
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in project.iterdir()}
    if mode == 'progress':
        notice = error_path.read_text()
        assert 'Repairing tests: starting' in notice
        assert 'Generated pytest: finished: 2 passed, 0 failed, 0 errors, 0 skipped (rc=0)' in notice
        assert '99' not in notice and str(project) not in notice
    elif mode == 'quiet':
        assert error_path.read_text() == ''
