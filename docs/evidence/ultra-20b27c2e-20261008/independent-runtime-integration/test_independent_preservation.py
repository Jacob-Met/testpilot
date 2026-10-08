"""Independent receiving checks: real pytest subprocesses and git apply."""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess

import pytest

import testpilot.loop as implementation
from testpilot.loop import TestPilot
from testpilot.model import ScriptedModel


PIN = 'dd79fbfbdcab00978b288835645c1b5adf37fec404ec0fa6da0ac41d45a79cbf'
CODE = 'def triple(number):\n    return number * 3\n'
DIFF = '--- /dev/null\n+++ b/arithmetic.py\n@@ -0,0 +1,2 @@\n+def triple(number):\n+    return number * 3\n'
GOOD = 'from arithmetic import triple\n\ndef test_value():\n    assert triple(7) == 21\n'
BAD = 'from arithmetic import triple\n\ndef test_value():\n    assert triple(7) == 22\n'
ORIGINAL = b'def test_original_regression():\n    assert 8 // 3 == 2\n'


def block(path, body):
    return '```python path=' + path + '\n' + body + '```\n'


@pytest.fixture
def repo(tmp_path):
    assert hashlib.sha256(Path(implementation.__file__).read_bytes()).hexdigest() == PIN
    root = tmp_path / 'beneficiary'
    (root / 'tests').mkdir(parents=True)
    (root / 'arithmetic.py').write_text(CODE)
    return root


def run(repo, replies, rounds=0):
    return TestPilot(ScriptedModel(['Pin the changed arithmetic behavior.', *replies]),
                     max_repair_rounds=rounds, timeout_s=20, coverage=False).run(repo, DIFF)


def apply_and_compare(repo, result, tmp_path, originals):
    subprocess.run(['git', 'init', '-q'], cwd=repo, check=True)
    patch = tmp_path / 'proposal.diff'
    patch.write_text(result.patch)
    subprocess.run(['git', 'apply', '--check', str(patch)], cwd=repo, check=True, capture_output=True)
    subprocess.run(['git', 'apply', str(patch)], cwd=repo, check=True, capture_output=True)
    for path, expected in originals.items():
        assert (repo / path).read_bytes() == expected
    for path, expected in result.test_files.items():
        assert path not in originals
        assert (repo / path).read_bytes() == expected.encode()


def test_numbered_alias_repair_preserves_an_omitted_second_failure(repo, tmp_path):
    originals = {'tests/test_value.py': ORIGINAL, 'tests/test_value_testpilot.py': ORIGINAL}
    for path, body in originals.items():
        (repo / path).write_bytes(body)
    first = block('tests/test_value.py', BAD) + block('tests/test_value_testpilot_2.py', BAD)
    repaired_alias = block('tests/test_value.py', GOOD)
    repaired_second = block('tests/test_value_testpilot_2.py', GOOD)

    result = run(repo, [first, repaired_alias, repaired_second], rounds=2)

    assert result.status == 'passed'
    assert result.rounds[1].result['failed'] == 1
    assert result.final['passed'] == 4 and result.tests_written == 2
    assert result.test_files == {'tests/test_value_testpilot_3.py': GOOD,
                                 'tests/test_value_testpilot_2.py': GOOD}
    assert result.rounds[1].contents['tests/test_value_testpilot_2.py'] == BAD
    apply_and_compare(repo, result, tmp_path, originals)


def test_conflicting_aliases_roll_back_the_entire_multifile_repair(repo, tmp_path):
    originals = {'tests/test_value.py': ORIGINAL}
    (repo / 'tests/test_value.py').write_bytes(ORIGINAL)
    first = block('tests/test_value.py', BAD) + block('tests/test_aux.py', BAD)
    # A valid independent update arrives first. The later alias disagreement
    # must preserve that file's previous bytes as well as the disputed file.
    repair = (block('tests/test_aux.py', GOOD) + block('tests/test_value.py', BAD)
              + block('tests/test_value_testpilot.py', GOOD))

    result = run(repo, [first, repair], rounds=1)

    assert result.status == 'failed' and 'conflicting repair blocks' in result.message
    assert result.test_files == {'tests/test_value_testpilot.py': BAD, 'tests/test_aux.py': BAD}
    assert result.final['failed'] == 2 and result.final['passed'] == 1
    assert result.rounds[-1].contents == result.rounds[0].contents
    apply_and_compare(repo, result, tmp_path, originals)


def test_identical_alias_and_canonical_repair_converges_to_one_file(repo, tmp_path):
    originals = {'tests/test_value.py': ORIGINAL}
    (repo / 'tests/test_value.py').write_bytes(ORIGINAL)
    initial = block('tests/test_value.py', BAD)
    repair = block('tests/test_value.py', GOOD) + block('tests/test_value_testpilot.py', GOOD)

    result = run(repo, [initial, repair], rounds=1)

    assert result.status == 'passed' and result.final['passed'] == 2
    assert result.tests_written == 1 and result.test_files == {'tests/test_value_testpilot.py': GOOD}
    apply_and_compare(repo, result, tmp_path, originals)


def test_new_repository_collision_in_partial_repair_keeps_prior_failed_file(repo, tmp_path):
    originals = {'tests/test_original.py': ORIGINAL}
    (repo / 'tests/test_original.py').write_bytes(ORIGINAL)
    result = run(repo, [block('tests/test_previous.py', BAD), block('tests/test_original.py', GOOD)], rounds=1)

    assert result.status == 'failed' and result.final['failed'] == 1
    assert result.final['passed'] == 2 and result.tests_written == 2
    assert result.test_files == {'tests/test_previous.py': BAD, 'tests/test_original_testpilot.py': GOOD}
    apply_and_compare(repo, result, tmp_path, originals)


def test_late_directory_collision_refuses_patch_and_retains_failed_evidence(repo):
    responses = iter(['Pin arithmetic.', block('tests/test_generated.py', BAD),
                      block('tests/test_generated.py', GOOD)])
    calls = 0

    def answer(model, messages):
        nonlocal calls
        calls += 1
        if calls == 3:
            (repo / 'tests/test_generated.py').mkdir()
        return next(responses)

    result = TestPilot(ScriptedModel(answer), max_repair_rounds=1,
                       timeout_s=20, coverage=False).run(repo, DIFF)

    assert result.status == 'failed' and result.patch == ''
    assert result.test_files == {'tests/test_generated.py': BAD}
    assert result.final['failed'] == 1
    assert (repo / 'tests/test_generated.py').is_dir()


def test_addition_patch_refuses_even_identical_later_destination(repo, tmp_path):
    result = run(repo, [block('tests/test_generated.py', GOOD)])
    assert result.status == 'passed'
    destination = repo / 'tests/test_generated.py'
    destination.write_text(GOOD)
    before = destination.stat().st_mtime_ns
    patch = tmp_path / 'proposal.diff'
    patch.write_text(result.patch)
    subprocess.run(['git', 'init', '-q'], cwd=repo, check=True)

    checked = subprocess.run(['git', 'apply', '--check', str(patch)], cwd=repo, capture_output=True)
    applied = subprocess.run(['git', 'apply', str(patch)], cwd=repo, capture_output=True)

    assert checked.returncode != 0 and applied.returncode != 0
    assert destination.read_bytes() == GOOD.encode()
    assert destination.stat().st_mtime_ns == before


def test_source_collision_after_green_run_prevents_publishable_patch(repo):
    pilot = TestPilot(ScriptedModel(['Pin arithmetic.', block('tests/test_generated.py', GOOD)]),
                      max_repair_rounds=0, timeout_s=20, coverage=False)
    native_run = pilot._run

    def run_then_create(root, files):
        result = native_run(root, files)
        if files:
            (root / 'tests/test_generated.py').write_bytes(b'# Other worker saved this after QA.\n')
        return result

    pilot._run = run_then_create
    result = pilot.run(repo, DIFF)

    assert result.final['ok'] is True
    assert result.status == 'failed' and not result.ok and result.patch == ''
    assert result.test_files == {'tests/test_generated.py': GOOD}
    assert (repo / 'tests/test_generated.py').read_bytes() == b'# Other worker saved this after QA.\n'
