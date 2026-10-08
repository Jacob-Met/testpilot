"""Exercise generated-test preservation through real pytest and git apply."""
import subprocess

import pytest

from testpilot.loop import TestPilot
from testpilot.model import ScriptedModel


SOURCE = "def double(value):\n    return value * 2\n"
DIFF = "--- /dev/null\n+++ b/m.py\n@@ -0,0 +1,2 @@\n+def double(value):\n+    return value * 2\n"
GOOD = "from m import double\n\ndef test_double():\n    assert double(2) == 4\n"
BAD = "from m import double\n\ndef test_double():\n    assert double(2) == 5\n"


def block(path, content):
    return f"```python path={path}\n{content}```"


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "m.py").write_text(SOURCE)
    (root / "tests").mkdir()
    return root


def run(repo, responses, *, rounds=0):
    return TestPilot(ScriptedModel(["Pin double's behavior.", *responses]),
                     max_repair_rounds=rounds, timeout_s=30, coverage=False).run(repo, DIFF)


def apply_patch(repo, patch, tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    path = tmp_path / "generated.patch"
    path.write_text(patch, encoding="utf-8")
    subprocess.run(["git", "apply", "--check", str(path)], cwd=repo, check=True)
    subprocess.run(["git", "apply", str(path)], cwd=repo, check=True)


@pytest.mark.parametrize("suggestion", ["tests/test_double.py", "./tests/test_double.py"])
def test_existing_failing_test_survives_generation_and_patch(repo, tmp_path, suggestion):
    original = b'def test_double():\n    assert False, "existing regression"\n'
    target = repo / "tests/test_double.py"
    target.write_bytes(original)

    result = run(repo, [block(suggestion, GOOD)])

    assert result.status == "failed"
    assert result.final["failed"] == 1 and result.final["passed"] == 1
    assert result.tests_written == 1
    assert "tests/test_double.py" not in result.test_files
    assert result.rounds[0].warnings
    assert target.read_bytes() == original
    apply_patch(repo, result.patch, tmp_path)
    assert target.read_bytes() == original
    for path, content in result.test_files.items():
        assert (repo / path).read_text() == content


def test_reserved_names_and_all_requested_files_survive(repo, tmp_path):
    originals = {
        "tests/test_double.py": b"def test_original():\n    assert True\n",
        "tests/test_double_testpilot.py": b"def test_other_original():\n    assert True\n",
    }
    for path, content in originals.items():
        (repo / path).write_bytes(content)
    reply = block("tests/test_double.py", GOOD) + "\n" + block("tests/test_double_testpilot_2.py", GOOD)

    result = run(repo, [reply])

    assert result.status == "passed" and result.final["passed"] == 4
    assert result.tests_written == 2 and len(result.test_files) == 2
    assert "tests/test_double_testpilot_2.py" in result.test_files
    assert not set(originals).intersection(result.test_files)
    apply_patch(repo, result.patch, tmp_path)
    for path, content in originals.items():
        assert (repo / path).read_bytes() == content


def test_partial_repair_keeps_unmentioned_failure(repo):
    first = block("tests/test_a.py", BAD) + "\n" + block("tests/test_b.py", BAD)

    result = run(repo, [first, block("tests/test_a.py", GOOD)], rounds=1)

    assert result.status == "failed" and result.repair_rounds_used == 1
    assert result.final["passed"] == 1 and result.final["failed"] == 1
    assert result.tests_written == 2
    assert result.test_files == {"tests/test_a.py": GOOD, "tests/test_b.py": BAD}
    assert result.rounds[0].contents["tests/test_a.py"] == BAD
    assert result.rounds[1].contents == result.test_files
    assert "+++ b/tests/test_b.py" in result.patch


def test_incremental_repairs_finish_the_whole_generated_suite(repo, tmp_path):
    first = block("tests/test_a.py", BAD) + "\n" + block("tests/test_b.py", BAD)

    result = run(repo, [first, block("tests/test_a.py", GOOD), block("tests/test_b.py", GOOD)], rounds=2)

    assert result.status == "passed" and result.repair_rounds_used == 2
    assert result.tests_written == 2 and result.final["passed"] == 2
    assert result.test_files == {"tests/test_a.py": GOOD, "tests/test_b.py": GOOD}
    assert result.rounds[1].result["failed"] == 1
    apply_patch(repo, result.patch, tmp_path)
    assert (repo / "tests/test_a.py").read_text() == GOOD
    assert (repo / "tests/test_b.py").read_text() == GOOD


@pytest.mark.parametrize("repair_path", ["./tests/test_double.py", "tests/test_double_testpilot.py"])
def test_repair_of_renamed_file_uses_stable_alias(repo, tmp_path, repair_path):
    target = repo / "tests/test_double.py"
    original = b"def test_original():\n    assert True\n"
    target.write_bytes(original)

    result = run(repo, [block("tests/test_double.py", BAD), block(repair_path, GOOD)], rounds=1)

    assert result.status == "passed" and result.final["passed"] == 2
    assert result.tests_written == 1 and len(result.test_files) == 1
    assert list(result.test_files.values()) == [GOOD]
    apply_patch(repo, result.patch, tmp_path)
    assert target.read_bytes() == original


def test_repair_can_add_a_file_without_losing_other_files(repo):
    first = block("tests/test_a.py", BAD) + "\n" + block("tests/test_b.py", GOOD)
    repair = block("tests/test_a.py", GOOD) + "\n" + block("tests/test_c.py", GOOD)

    result = run(repo, [first, repair], rounds=1)

    assert result.status == "passed" and result.final["passed"] == 3
    assert result.tests_written == 3
    assert result.test_files == {"tests/test_a.py": GOOD, "tests/test_b.py": GOOD, "tests/test_c.py": GOOD}


def test_new_filename_in_repair_does_not_remove_failing_file(repo):
    result = run(repo, [block("tests/test_a.py", BAD), block("tests/test_b.py", GOOD)], rounds=1)

    assert result.status == "failed" and result.final["failed"] == 1
    assert result.final["passed"] == 1 and result.tests_written == 2
    assert result.test_files == {"tests/test_a.py": BAD, "tests/test_b.py": GOOD}


def test_code_bug_verdict_keeps_all_generated_evidence(repo):
    first = block("tests/test_a.py", GOOD) + "\n" + block("tests/test_b.py", BAD)
    result = run(repo, [first, "VERDICT: CODE_BUG\nKeep the failing regression for review."], rounds=1)

    assert result.status == "suspected_code_bug"
    assert result.final["passed"] == 1 and result.final["failed"] == 1
    assert result.test_files == {"tests/test_a.py": GOOD, "tests/test_b.py": BAD}
    assert "+++ b/tests/test_a.py" in result.patch and "+++ b/tests/test_b.py" in result.patch


def test_model_error_after_partial_repair_preserves_work(repo):
    first = block("tests/test_a.py", BAD) + "\n" + block("tests/test_b.py", BAD)
    result = run(repo, [first, block("tests/test_a.py", GOOD)], rounds=2)

    assert result.status == "model_error"
    assert result.test_files == {"tests/test_a.py": GOOD, "tests/test_b.py": BAD}
    assert result.final["passed"] == 1 and result.final["failed"] == 1


def symlink(target, link):
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")


def test_nested_symlink_is_relocated_without_touching_its_target(repo, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    original = b"def test_original():\n    assert True\n"
    target = outside / "test_double.py"
    target.write_bytes(original)
    link = repo / "tests/linked"
    symlink(outside, link)

    result = run(repo, [block("tests/linked/test_double.py", GOOD)])

    assert result.status == "passed" and result.final["passed"] == 2
    assert "tests/linked/test_double.py" not in result.test_files
    apply_patch(repo, result.patch, tmp_path)
    assert link.is_symlink() and target.read_bytes() == original


def test_symlinked_tests_root_is_refused_without_a_patch(repo, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    original = b"def test_original():\n    assert True\n"
    target = outside / "test_double.py"
    target.write_bytes(original)
    (repo / "tests").rmdir()
    symlink(outside, repo / "tests")

    result = run(repo, [block("tests/test_double.py", GOOD)])

    assert result.status == "failed" and "regular directory" in result.message
    assert result.patch == "" and result.test_files == {}
    assert (repo / "tests").is_symlink() and target.read_bytes() == original


def test_file_blocking_a_parent_directory_is_preserved(repo, tmp_path):
    target = repo / "tests/unit"
    target.write_bytes(b"reserved repository file\n")

    result = run(repo, [block("tests/unit/test_double.py", GOOD)])

    assert result.status == "passed" and result.final["passed"] == 1
    assert "tests/unit/test_double.py" not in result.test_files
    apply_patch(repo, result.patch, tmp_path)
    assert target.read_bytes() == b"reserved repository file\n"


def test_path_occupied_during_repair_is_not_overwritten(repo):
    target = repo / "tests/test_double.py"
    responses = iter(["Pin double.", block("tests/test_double.py", BAD), block("tests/test_double.py", GOOD)])
    calls = 0

    def answer(model, messages):
        nonlocal calls
        calls += 1
        if calls == 3:
            target.write_bytes(b"# New repository file from concurrent work.\n")
        return next(responses)

    result = TestPilot(ScriptedModel(answer), max_repair_rounds=1, timeout_s=30,
                       coverage=False).run(repo, DIFF)

    assert result.status == "failed" and "replacing repository path" in result.message
    assert result.patch == "" and result.test_files == {"tests/test_double.py": BAD}
    assert target.read_bytes() == b"# New repository file from concurrent work.\n"


def test_git_refuses_patch_if_a_file_appears_after_generation(repo, tmp_path):
    result = run(repo, [block("tests/test_double.py", GOOD)])
    assert result.status == "passed"
    target = repo / "tests/test_double.py"
    original = b"# Work saved after TestPilot completed.\n"
    target.write_bytes(original)
    path = tmp_path / "generated.patch"
    path.write_text(result.patch)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    applied = subprocess.run(["git", "apply", str(path)], cwd=repo, capture_output=True)

    assert applied.returncode != 0
    assert target.read_bytes() == original
