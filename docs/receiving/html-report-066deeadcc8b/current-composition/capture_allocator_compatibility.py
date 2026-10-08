"""Narrow PR20 compatibility derivative of the frozen author CLI driver; same-basename modules and a partial repair alias."""
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
    plan = 'Review generated files that share a basename while retaining local fixtures and a partial repair alias.'
    unit = "from m import double\n\ndef test_unit(operand):\n    assert double(operand) == 6\n"
    integration = "from m import double\n\ndef test_integration(operand):\n    assert double(operand) == 10\n"
    good = "```python path=tests/unit/test_calc.py\nfrom m import double\n\ndef test_unit(operand):\n    assert double(operand) == 6\n```\n```python path=tests/integration/test_calc.py\nfrom m import double\n\ndef test_integration(operand):\n    assert double(operand) == 10\n```"
    bad = "```python path=tests/unit/test_calc.py\nfrom m import double\n\ndef test_unit(operand):\n    assert double(operand) == 7\n```\n```python path=tests/integration/test_calc.py\nfrom m import double\n\ndef test_integration(operand):\n    assert double(operand) == 10\n```"
    partial = "```python path=tests/unit/test_calc.py\nfrom m import double\n\ndef test_unit(operand):\n    assert double(operand) == 6\n```"
    cases = {
        'passed': ([plan, good], ['--rounds', '1'], 'passed'),
        'repair': ([plan, bad, partial], ['--rounds', '1'], 'passed'),
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
        source_text = 'def double(x):\n    return x * 2\n'
        (repo / 'm.py').write_text(source_text)
        (repo / 'legacy').mkdir()
        (repo / 'legacy/test_calc.py').write_text('from m import double\n\ndef test_existing():\n    assert double(2) == 4\n')
        for location, operand in [('unit', 3), ('integration', 5)]:
            target = repo / 'tests' / location
            target.mkdir()
            (target / 'conftest.py').write_text(f'import pytest\n\n@pytest.fixture\ndef operand():\n    return {operand}\n')
        diff = '--- /dev/null\n+++ b/m.py\n@@ -0,0 +1,2 @@\n' + ''.join('+' + line for line in source_text.splitlines(keepends=True))
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
        expected_files = {'tests/unit/test_calc_testpilot.py': unit,
                          'tests/integration/test_calc_testpilot_2.py': integration}
        assert result['test_files'] == expected_files, (name, result['test_files'])
        assert result['final']['junit_available'] is True
        assert result['final']['passed'] == 3
        assert result['final']['failed'] == result['final']['errors'] == 0
        assert result['final']['generated']['collected'] == result['final']['generated']['passed'] == 2
        assert result['tests_written'] == 2
        assert result['repair_rounds_used'] == (1 if name == 'repair' else 0)
        assert len(result['rounds']) == (2 if name == 'repair' else 1)
        assert result['rounds'][0]['contents']['tests/unit/test_calc_testpilot.py'] == (unit.replace('== 6', '== 7') if name == 'repair' else unit)
        for requested, resolved in [('tests/unit/test_calc.py', 'tests/unit/test_calc_testpilot.py'),
                                    ('tests/integration/test_calc.py', 'tests/integration/test_calc_testpilot_2.py')]:
            assert any(repr(requested) in w and repr(resolved) in w for w in result['rounds'][0]['warnings'])
        if name == 'repair':
            assert result['rounds'][0]['result']['failed'] == 1
            assert result['rounds'][0]['result']['passed'] == 2
            assert result['rounds'][0]['result']['errors'] == 0
        report.setdefault('compatibility', {})[name] = {'resolved_files': list(expected_files),
            'total_passed': result['final']['passed'], 'generated_passed': result['final']['generated']['passed'],
            'repair_rounds_used': result['repair_rounds_used'], 'initial_warnings': result['rounds'][0]['warnings'],
            'initial_failed': result['rounds'][0]['result']['failed'],
            'initial_contents': result['rounds'][0]['contents'], 'final_contents': result['test_files']}
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
