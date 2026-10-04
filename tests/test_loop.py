import subprocess
import sys

import pytest

from testpilot.loop import (DEFAULT_TEST_PATH, Ledger, TestPilot, make_patch, parse_test_files, parse_verdict,
                            render_report, sanitize_test_path, write_outputs)
from testpilot.model import RoutingConfig, ScriptedModel, Usage
from testpilot.sandbox import coverage_available

SRC = "def double(x):\n    return x * 2\n"
DIFF = "--- /dev/null\n+++ b/m.py\n@@ -0,0 +1,2 @@\n+def double(x):\n+    return x * 2\n"
GOOD = "```python path=tests/test_double.py\nfrom m import double\n\n\ndef test_d():\n    assert double(2) == 4\n```"
BAD = "```python path=tests/test_double.py\nfrom m import double\n\n\ndef test_d():\n    assert double(2) == 5\n```"
PLAN = "1. double(2) == 4"


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "m.py").write_text(SRC)
    return tmp_path


def pilot(responses, **kw):
    kw.setdefault("coverage", False)
    kw.setdefault("timeout_s", 30)
    return TestPilot(ScriptedModel(responses), RoutingConfig(planner_model="P", editor_model="E"), **kw)


def test_passes_first_try(repo):
    p = pilot([PLAN, GOOD])
    r = p.run(repo, DIFF)
    assert r.status == "passed" and r.ok and r.repair_rounds_used == 0 and r.tests_written == 1
    assert [c[0] for c in p.client.calls] == ["P", "E"]  # planner -> editor routing
    assert "+++ b/tests/test_double.py" in r.patch and "new file mode" in r.patch
    assert r.ledger["by_model"]["P"]["calls"] == 1 and r.ledger["total_tokens"] > 0


def test_repair_then_pass(repo):
    p = pilot([PLAN, BAD, "fixed:\n" + GOOD])
    r = p.run(repo, DIFF)
    assert r.status == "passed" and r.repair_rounds_used == 1
    assert [x.kind for x in r.rounds] == ["generate", "repair"]
    assert p.client.calls[2][0] == "E"
    assert "assert 4 == 5" in p.client.calls[2][1][1]["content"]  # failure report fed to the repairer
    assert "== 5" in r.rounds[0].contents["tests/test_double.py"]


def test_round_limit(repo):
    r = pilot([PLAN, BAD, BAD, BAD], max_repair_rounds=2).run(repo, DIFF)
    assert r.status == "failed" and r.repair_rounds_used == 2 and "2 repair round" in r.message


def test_zero_rounds(repo):
    r = pilot([PLAN, BAD], max_repair_rounds=0).run(repo, DIFF)
    assert r.status == "failed" and r.repair_rounds_used == 0


def test_code_bug_verdict(repo):
    r = pilot([PLAN, BAD, "VERDICT: CODE_BUG\ndouble is wrong"]).run(repo, DIFF)
    assert r.status == "suspected_code_bug" and r.message == "double is wrong" and r.patch


def test_repair_without_code_keeps_tests(repo):
    r = pilot([PLAN, BAD, "no idea", GOOD]).run(repo, DIFF)
    assert r.status == "passed" and r.repair_rounds_used == 2
    assert "no code block" in r.rounds[1].warnings[0]


def test_no_changes_and_no_tests(repo):
    assert pilot([]).run(repo, "").status == "no_changes"
    assert pilot([PLAN, "I cannot help"]).run(repo, DIFF).status == "no_tests"


def test_model_error_and_budget(repo):
    assert pilot([PLAN]).run(repo, DIFF).status == "model_error"  # script exhausted
    r = pilot([PLAN, GOOD], max_total_tokens=1).run(repo, DIFF)
    assert r.status == "budget_exhausted" and len(r.ledger["entries"]) == 1


def test_parse_test_files():
    text = ("```python path=tests/test_a.py\na = 1\n```\n```bash\nrm -rf /\n```\n"
            "```python\n# file: tests/test_b.py\nb = 2\n```\n```py path=../../etc/x.py\nc\n```\n```\nd\n```")
    files, warns = parse_test_files(text)
    assert files == {"tests/test_a.py": "a = 1\n", "tests/test_b.py": "b = 2\n", "tests/test_x.py": "c\n",
                     DEFAULT_TEST_PATH: "d\n"}
    assert any("../../etc/x.py" in w for w in warns)


def test_sanitize_and_verdict():
    assert sanitize_test_path("tests/unit/test_ok.py") == ("tests/unit/test_ok.py", None)
    assert sanitize_test_path("m.py")[0] == "tests/test_m.py"
    assert sanitize_test_path("/abs/test_z.py")[0] == "tests/test_z.py"
    assert parse_verdict("ok") is None
    assert parse_verdict("VERDICT: CODE_BUG") == "model reported a code bug"


def test_ledger_costs():
    led = Ledger(RoutingConfig(prices={"P": (1.0, 4.0)}))
    led.record("planner", "P", Usage(1000, 500))
    led.record("editor", "E", Usage(10, 10))
    d = led.to_dict()
    assert d["total_tokens"] == 1520 and d["total_cost_usd"] == pytest.approx(0.003)
    assert d["cost_is_complete"] is False  # E has no price


def test_patch_applies_with_git(repo, tmp_path):
    (repo / "tests").mkdir()
    (repo / "tests" / "test_old.py").write_text("x = 1\n")
    patch = make_patch(repo, {"tests/test_old.py": "x = 2\n", "tests/test_new.py": "y = 1\n"})
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (tmp_path / "p.diff").write_text(patch)
    subprocess.run(["git", "apply", str(tmp_path / "p.diff")], cwd=repo, check=True)
    assert (repo / "tests" / "test_old.py").read_text() == "x = 2\n"
    assert (repo / "tests" / "test_new.py").read_text() == "y = 1\n"


@pytest.mark.skipif(not coverage_available(sys.executable), reason="coverage not installed")
def test_coverage_delta_and_outputs(repo, tmp_path):
    r = pilot([PLAN, GOOD], coverage=True).run(repo, DIFF)
    assert r.coverage is not None
    assert r.coverage["changed_lines_after"] == 100.0
    assert r.coverage["total_after"] >= r.coverage["total_before"]
    paths = write_outputs(r, tmp_path / "out")
    assert paths["patch"].read_text() == r.patch
    md = render_report(r)
    assert "Coverage (changed lines" in md and "```diff" in md
