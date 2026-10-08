"""Receive generated module names through real pytest, repairs, and git apply."""
import subprocess

import pytest

from testpilot.loop import TestPilot
from testpilot.model import ScriptedModel
from testpilot.sandbox import run_pytest


SOURCE = "def double(value):\n    return value * 2\n"
DIFF = "--- /dev/null\n+++ b/m.py\n@@ -0,0 +1,2 @@\n+def double(value):\n+    return value * 2\n"
GOOD = "from m import double\n\ndef test_double():\n    assert double(3) == 6\n"
BAD = "from m import double\n\ndef test_double():\n    assert double(3) == 7\n"


def put(repo, path, content):
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def block(path, content):
    return f"```python path={path}\n{content}```"


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    put(root, "m.py", SOURCE)
    return root


def originals(repo):
    return {p.relative_to(repo).as_posix(): p.read_bytes()
            for p in repo.rglob("*") if p.is_file()}


def generate(repo, replies, *, repairs=0):
    return TestPilot(ScriptedModel(["Pin double's behavior.", *replies]),
                     max_repair_rounds=repairs, timeout_s=30,
                     coverage=False).run(repo, DIFF)


def assert_passed(result, *, generated, total):
    assert result.status == "passed", (result.message, result.final)
    assert result.final["returncode"] == 0
    assert result.final["errors"] == result.final["failed"] == result.final["skipped"] == 0
    assert result.final["passed"] == total
    assert result.final["generated"]["passed"] == generated
    assert result.tests_written == generated


def apply_and_receive(repo, result, before, tmp_path, total):
    for path, content in before.items():
        assert (repo / path).read_bytes() == content
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    patch = tmp_path / "generated.patch"
    patch.write_text(result.patch, encoding="utf-8")
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=repo, check=True)
    subprocess.run(["git", "apply", str(patch)], cwd=repo, check=True)
    for path, content in before.items():
        assert (repo / path).read_bytes() == content
    for path, content in result.test_files.items():
        assert (repo / path).read_text(encoding="utf-8") == content
    received = run_pytest(repo, coverage=False, timeout=30)
    assert received.ok, received.output
    assert received.passed == total
    assert received.failed == received.errors == received.skipped == 0


def test_two_generated_standalone_modules_keep_both_local_fixtures(repo, tmp_path):
    put(repo, "tests/unit/conftest.py",
        "import pytest\n\n@pytest.fixture\ndef operand():\n    return 3\n")
    put(repo, "tests/integration/conftest.py",
        "import pytest\n\n@pytest.fixture\ndef operand():\n    return 5\n")
    unit = "from m import double\n\ndef test_unit(operand):\n    assert double(operand) == 6\n"
    integration = "from m import double\n\ndef test_integration(operand):\n    assert double(operand) == 10\n"
    before = originals(repo)

    result = generate(repo, [block("tests/unit/test_calc.py", unit) + "\n" +
                             block("tests/integration/test_calc.py", integration)])

    assert_passed(result, generated=2, total=2)
    assert result.test_files == {
        "tests/unit/test_calc.py": unit,
        "tests/integration/test_calc_testpilot.py": integration,
    }
    assert result.rounds[0].warnings
    apply_and_receive(repo, result, before, tmp_path, 2)


def test_existing_nested_modules_reserve_suffixes_and_keep_generated_fixture_scope(repo, tmp_path):
    put(repo, "legacy/test_calc.py", GOOD)
    put(repo, "legacy/nested/test_calc_testpilot.py", GOOD)
    put(repo, "tests/unit/conftest.py",
        "import pytest\n\n@pytest.fixture\ndef operand():\n    return 21\n")
    content = "from m import double\n\ndef test_fixture(operand):\n    assert double(operand) == 42\n"
    before = originals(repo)

    result = generate(repo, [block("tests/unit/test_calc.py", content)])

    assert_passed(result, generated=1, total=3)
    assert result.test_files == {"tests/unit/test_calc_testpilot_2.py": content}
    apply_and_receive(repo, result, before, tmp_path, 3)


def test_renaming_does_not_steal_another_requested_module_name(repo, tmp_path):
    put(repo, "legacy/test_calc.py", GOOD)
    before = originals(repo)
    requested = "tests/integration/test_calc_testpilot.py"

    result = generate(repo, [block("tests/unit/test_calc.py", GOOD) + "\n" +
                             block(requested, GOOD)])

    assert_passed(result, generated=2, total=3)
    assert result.test_files == {
        "tests/unit/test_calc_testpilot_2.py": GOOD,
        requested: GOOD,
    }
    apply_and_receive(repo, result, before, tmp_path, 3)


def test_existing_path_relocation_also_avoids_other_directory_module_names(repo, tmp_path):
    put(repo, "tests/unit/test_calc.py", GOOD)
    put(repo, "legacy/test_calc_testpilot.py", GOOD)
    before = originals(repo)

    result = generate(repo, [block("tests/unit/test_calc.py", GOOD)])

    assert_passed(result, generated=1, total=3)
    assert result.test_files == {"tests/test_calc_testpilot_2.py": GOOD}
    apply_and_receive(repo, result, before, tmp_path, 3)


@pytest.mark.parametrize("repair_path", [
    "tests/unit/test_calc.py",
    "tests/unit/test_calc_testpilot.py",
])
def test_module_rename_preserves_original_and_resolved_partial_repair_aliases(repo, tmp_path, repair_path):
    put(repo, "legacy/test_calc.py", GOOD)
    before = originals(repo)
    first = block("tests/unit/test_calc.py", BAD) + "\n" + block("tests/test_other.py", GOOD)

    result = generate(repo, [first, block(repair_path, GOOD)], repairs=1)

    assert_passed(result, generated=2, total=3)
    assert result.repair_rounds_used == 1
    assert result.rounds[0].result["failed"] == 1
    assert result.rounds[0].result["errors"] == 0
    assert result.rounds[0].result["passed"] == 2
    assert result.rounds[0].contents["tests/unit/test_calc_testpilot.py"] == BAD
    assert result.test_files == {
        "tests/unit/test_calc_testpilot.py": GOOD,
        "tests/test_other.py": GOOD,
    }
    apply_and_receive(repo, result, before, tmp_path, 3)


@pytest.mark.parametrize("outer_package", [False, True])
def test_distinct_regular_packages_keep_same_basenames_and_relative_imports(repo, tmp_path, outer_package):
    if outer_package:
        put(repo, "tests/__init__.py", "")
    for name, operand in [("unit", 3), ("integration", 5)]:
        put(repo, f"tests/{name}/__init__.py", "")
        put(repo, f"tests/{name}/helpers.py", f"OPERAND = {operand}\n")
    before = originals(repo)
    unit = ("from m import double\nfrom .helpers import OPERAND\n\n"
            "def test_unit():\n    assert double(OPERAND) == 6\n")
    integration = ("from m import double\nfrom .helpers import OPERAND\n\n"
                   "def test_integration():\n    assert double(OPERAND) == 10\n")

    result = generate(repo, [block("tests/unit/test_calc.py", unit) + "\n" +
                             block("tests/integration/test_calc.py", integration)])

    assert_passed(result, generated=2, total=2)
    assert result.test_files == {
        "tests/unit/test_calc.py": unit,
        "tests/integration/test_calc.py": integration,
    }
    assert result.rounds[0].warnings == []
    apply_and_receive(repo, result, before, tmp_path, 2)


def test_existing_packaged_module_does_not_reserve_unrelated_standalone_basename(repo, tmp_path):
    put(repo, "tests/packaged/__init__.py", "")
    put(repo, "tests/packaged/test_calc.py", GOOD)
    before = originals(repo)

    result = generate(repo, [block("tests/standalone/test_calc.py", GOOD)])

    assert_passed(result, generated=1, total=2)
    assert result.test_files == {"tests/standalone/test_calc.py": GOOD}
    assert result.rounds[0].warnings == []
    apply_and_receive(repo, result, before, tmp_path, 2)
