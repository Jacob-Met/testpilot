"""Capture actual authored ScriptedModel CLI runs in a new private directory."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def sha(data):
    return hashlib.sha256(data).hexdigest()


def files(root):
    return {str(p.relative_to(root)): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
            for p in sorted(root.rglob('*')) if p.is_file() and '.git' not in p.parts
            and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--python', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--expect-html', action='store_true')
    args = ap.parse_args()
    source = args.source.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    env = {k: v for k, v in os.environ.items()
           if not k.startswith('TESTPILOT_') and not any(x in k.upper() for x in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD', 'CREDENTIAL'))}
    env.update(PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE='1')
    plan = 'Check the changed doubling function with one runnable boundary assertion.'
    good = '```python path=tests/test_generated.py\nfrom m import double\n\ndef test_double():\n    assert double(2) == 4\n```'
    bad = good.replace('== 4', '== 5')
    hang = '```python path=tests/test_generated.py\ndef test_hang():\n    while True:\n        pass\n```'
    cases = {
        'passed': ([plan, good], [], 'passed'),
        'repair': ([plan, bad, good], [], 'passed'),
        'failed': ([plan, bad], ['--rounds', '0'], 'failed'),
        'suspected': ([plan, good, 'VERDICT: CODE_BUG\nThe changed implementation adds one to every doubled result.'], [], 'suspected_code_bug'),
        'no_tests': ([plan, 'No test code was generated.'], [], 'no_tests'),
        'no_changes': ([plan], [], 'no_changes'),
        'budget': ([plan, good], ['--max-tokens', '1'], 'budget_exhausted'),
        'model_error': ([plan], [], 'model_error'),
        'timeout': ([plan, hang], ['--rounds', '0', '--timeout', '2'], 'failed'),
    }
    source_before = files(source)
    report = {'schema': 'testpilot.html_report.author_cli.v1', 'source': str(source),
              'python': str(args.python), 'driver_sha256': sha(Path(__file__).read_bytes()),
              'expect_html': args.expect_html, 'cases': [], 'source_before': source_before}
    for name, (replies, extra, status) in cases.items():
        root = args.output / name
        repo = root / 'repo'
        script = root / 'script'
        (repo / 'tests').mkdir(parents=True)
        script.mkdir()
        source_text = 'def double(x):\n    return x * 2' + (' + 1' if name == 'suspected' else '') + '\n'
        (repo / 'm.py').write_text(source_text)
        (repo / 'tests/test_existing.py').write_text('from m import double\n\ndef test_existing():\n    assert callable(double)\n')
        diff = '' if name == 'no_changes' else '--- /dev/null\n+++ b/m.py\n@@ -0,0 +1,2 @@\n' + ''.join('+' + line for line in source_text.splitlines(keepends=True))
        diff_path = root / 'change.diff'
        diff_path.write_text(diff)
        for i, reply in enumerate(replies):
            (script / f'{i + 1:02d}.md').write_text(reply)
        subprocess.run(['git', 'init', '-q'], cwd=repo, check=True, env=env)
        input_before = files(repo)
        argv = [str(args.python), '-B', '-m', 'testpilot', 'run', '--repo', str(repo),
                '--diff', str(diff_path), '--backend', 'scripted', '--script', str(script),
                '--timeout', '30', '--out', str(root / 'out'), *extra]
        start = time.monotonic()
        run = subprocess.run(argv, cwd=source, env=env, capture_output=True, timeout=50)
        (root / 'stdout.txt').write_bytes(run.stdout)
        (root / 'stderr.txt').write_bytes(run.stderr)
        result = json.loads((root / 'out/report.json').read_bytes())
        assert result['status'] == status, (name, result['status'], run.stderr.decode(errors='replace'))
        assert run.returncode == (0 if status == 'passed' else 1), name
        assert (root / 'out/report.html').exists() == args.expect_html, name
        assert files(repo) == input_before, name
        patch_check = None
        if result['patch']:
            check = subprocess.run(['git', 'apply', '--check', str(root / 'out/testpilot.patch')],
                                   cwd=repo, env=env, capture_output=True)
            assert check.returncode == 0, (name, check.stderr)
            patch_check = {'exit_code': check.returncode, 'stderr': check.stderr.decode()}
        report['cases'].append({'name': name, 'argv': argv, 'exit_code': run.returncode,
                                'elapsed_seconds': time.monotonic() - start, 'status': result['status'],
                                'final': result['final'], 'tests_written': result['tests_written'],
                                'repair_rounds_used': result['repair_rounds_used'], 'inputs': input_before,
                                'artifacts': files(root / 'out'), 'git_apply_check': patch_check})
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(name, run.returncode, result['status'], flush=True)
    report['source_after'] = files(source)
    assert report['source_before'] == report['source_after']
    report['passed'] = len(report['cases'])
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
