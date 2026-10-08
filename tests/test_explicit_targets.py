import json

import pytest

from testpilot.diff import changed_functions
from testpilot.html_report import render_html_report
from testpilot.loop import TestPilot, render_report
from testpilot.model import ScriptedModel
from testpilot.targets import SELECTION_REASON, TargetSelectionError, resolve_targets

SOURCE = "LIMIT = 50\n\n\ndef accepts(amount):\n    return amount <= LIMIT\n\n\ndef other():\n    return 2\n"
DIFF = "--- a/settings.py\n+++ b/settings.py\n@@ -1 +1 @@\n-LIMIT = 100\n+LIMIT = 50\n"
FENCE = chr(96) * 3
GOOD = (FENCE + "python path=tests/test_selected.py\nfrom settings import accepts\n\n\n"
        "def test_accepts():\n    assert accepts(50)\n    assert not accepts(75)\n" + FENCE)
BAD = GOOD.replace("assert not accepts(75)", "assert accepts(75)")


def test_current_selection_order_and_real_added_lines(tmp_path):
    (tmp_path / "settings.py").write_text(SOURCE)
    assert changed_functions(tmp_path, DIFF) == []
    chosen = resolve_targets(tmp_path, DIFF, [
        "settings.py::other", "./settings.py::accepts", "settings.py::other"])
    assert [f.qualname for f in chosen] == ["other", "accepts"]
    assert [f.changed_lines for f in chosen] == [[], []]
    assert chosen[1].path == "settings.py"
    assert chosen[1].source == "def accepts(amount):\n    return amount <= LIMIT"
    changed = DIFF + "@@ -9 +9 @@\n-    return 1\n+    return 2\n"
    assert resolve_targets(tmp_path, changed, ["settings.py::other"])[0].changed_lines == [9]


def test_native_discovery_encoding_and_ambiguity(tmp_path):
    source = ("# coding: latin-1\nclass Café:\n    @staticmethod\n"
              "    def réponse():\n        return 'déjà'\n")
    (tmp_path / "encoded.py").write_bytes(source.encode("latin-1"))
    function = resolve_targets(tmp_path, "", ["encoded.py::Café.réponse"])[0]
    assert function.is_method and function.lineno == 3 and function.end_lineno == 5
    assert function.source == "    @staticmethod\n    def réponse():\n        return 'déjà'"
    (tmp_path / "branches.py").write_text(
        "if True:\n    def selected(): return 1\nelse:\n    def selected(): return 2\n")
    with pytest.raises(TargetSelectionError, match="ambiguous"):
        resolve_targets(tmp_path, "", ["branches.py::selected"])


@pytest.mark.parametrize("spec", ["settings.py", "settings.py::missing", "settings.py::accepts.inner",
                                  "../outside.py::f", "tests/test_sample.py::f"])
def test_invalid_requests_refuse_without_execution(tmp_path, spec):
    (tmp_path / "settings.py").write_text(SOURCE)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_sample.py").write_text("raise RuntimeError('never import')\ndef f(): pass\n")
    client = ScriptedModel([])
    pilot = TestPilot(client, coverage=False)
    pilot._run = lambda *args: pytest.fail("invalid target reached test execution")
    with pytest.raises(TargetSelectionError):
        pilot.run(tmp_path, DIFF, targets=[spec])
    assert client.calls == []


def test_aliases_cannot_select_test_sources(tmp_path):
    (tmp_path / "tests").mkdir()
    target = tmp_path / "tests" / "helper.py"
    target.write_text("def f(): pass\n")
    (tmp_path / "alias.py").symlink_to(target)
    with pytest.raises(TargetSelectionError, match="test source"):
        resolve_targets(tmp_path, "", ["alias.py::f"])


def test_actual_context_repair_and_saved_selection(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "settings.py").write_text(SOURCE)
    client = ScriptedModel(["Test the supplied new limit of 50.", BAD, GOOD])
    specs = ["settings.py::accepts"]
    result = TestPilot(client, max_repair_rounds=1, timeout_s=30, coverage=False).run(
        repo, DIFF, targets=specs)
    assert result.status == "passed" and result.tests_written == 1 and result.repair_rounds_used == 1
    assert result.changed_functions[0]["changed_lines"] == []
    assert len(client.calls) == 3
    for _, messages in client.calls:
        assert "explicitly chosen" in messages[0]["content"]
        assert SELECTION_REASON in messages[1]["content"]
        assert DIFF in messages[1]["content"]
        assert result.changed_functions[0]["source"] in messages[1]["content"]
        assert "def other" not in messages[1]["content"]
    assert "assert False" in client.calls[2][1][1]["content"]
    specs.append("settings.py::other")
    assert result.to_dict()["selection"]["requested"] == ["settings.py::accepts"]
    assert result.to_dict()["selection"]["diff_text"] == DIFF
    assert "Caller-selected functions: settings.py::accepts" in render_report(result)
    html = render_html_report(json.dumps(result.to_dict()).encode(), result.patch.encode())
    assert SELECTION_REASON in html and "Supplied diff context" in html
    assert not (repo / "tests").exists()
    assert (repo / "settings.py").read_text() == SOURCE


def test_automatic_no_change_keeps_original_schema(tmp_path):
    (tmp_path / "settings.py").write_text(SOURCE)
    client = ScriptedModel([])
    result = TestPilot(client).run(tmp_path, DIFF)
    assert result.status == "no_changes" and result.changed_functions == []
    assert "selection" not in result.to_dict() and client.calls == []
    assert "- Changed functions: none" in render_report(result)
