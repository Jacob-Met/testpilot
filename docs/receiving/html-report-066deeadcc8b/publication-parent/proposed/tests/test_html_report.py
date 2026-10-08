import base64
import copy
import json
from html.parser import HTMLParser

import pytest

from testpilot.html_report import render_html_report
from testpilot.loop import Ledger, LoopResult, RoundRecord, render_report, write_outputs
from testpilot.model import RoutingConfig, Usage
from testpilot.sandbox import CaseResult, SandboxResult


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)

    def downloads(self):
        return {attrs['download']: base64.b64decode(attrs['href'].split(',', 1)[1])
                for tag, attrs in self.tags if tag == 'a' and 'download' in attrs}


def result():
    old = 'from m import double\n\ndef test_double():\n    assert double(2) == 5\n'
    new = old.replace('== 5', '== 4')
    first = SandboxResult(1, False, .12, 30, 'first failure',
                          [CaseResult('tests/test_double.py::test_double', 'failed', 'assert 4 == 5', 'tests/test_double.py')],
                          generated_files=['tests/test_double.py'], junit_available=True).to_dict()
    final = SandboxResult(0, False, .13, 30, 'final output',
                          [CaseResult('checks/test_existing.py::test_old', 'passed'),
                           CaseResult('tests/test_double.py::test_double', 'passed', generated_file='tests/test_double.py')],
                          generated_files=['tests/test_double.py'], junit_available=True).to_dict()
    ledger = Ledger(RoutingConfig(planner_model='P', editor_model='E'))
    ledger.record('planner', 'P', Usage(12, 8, True))
    ledger.record('editor', 'E', Usage(30, 20, True))
    return LoopResult('passed', [{'path': 'm.py', 'qualname': 'double', 'lineno': 1, 'end_lineno': 2,
                                  'source': 'def double(x):\n    return x * 2\n'}],
                      1, 3, {'tests/test_double.py': new}, 1, final,
                      'diff --git a/tests/test_double.py b/tests/test_double.py\nnew file mode 100644\n',
                      None, ledger.to_dict(),
                      [RoundRecord(0, 'generate', ['tests/test_double.py'], first, [], {'tests/test_double.py': old}),
                       RoundRecord(1, 'repair', ['tests/test_double.py'], final, [], {'tests/test_double.py': new})],
                      'Check doubling positive and zero values.')


def rendered(res):
    data = json.dumps(res.to_dict(), indent=2).encode('utf-8')
    return render_html_report(data, res.patch.encode('utf-8'))


def test_writer_preserves_existing_artifacts_and_result(tmp_path):
    res = result()
    before = copy.deepcopy(res.to_dict())
    paths = write_outputs(res, tmp_path)
    assert set(paths) == {'patch', 'json', 'md', 'html'}
    assert paths['patch'].read_text() == res.patch
    assert paths['json'].read_text() == json.dumps(before, indent=2)
    assert paths['md'].read_text() == render_report(res)
    assert res.to_dict() == before
    downloads = Document(paths['html'].read_text()).downloads()
    assert downloads == {'testpilot.patch': paths['patch'].read_bytes(), 'report.json': paths['json'].read_bytes()}


def test_exact_embedded_bytes_include_native_newlines_and_final_newline_choice():
    res = result()
    raw_json = json.dumps(res.to_dict(), indent=2).replace('\n', '\r\n').encode('utf-8')
    raw_patch = res.patch.replace('\n', '\r\n').encode('utf-8')
    downloads = Document(render_html_report(raw_json, raw_patch)).downloads()
    assert downloads['report.json'] == raw_json
    assert downloads['testpilot.patch'] == raw_patch


def test_generated_execution_and_other_selected_cases_remain_distinct():
    doc = Document(rendered(result()))
    text = ''.join(doc.text)
    assert '1 / 1' in text
    assert 'Generated test' in text and 'Other selected test' in text
    assert 'checks/test_existing.py::test_old' in text
    assert 'Recorded selected-suite case counts' in text
    assert 'Recorded generated-case counts' in text


def test_complete_source_snapshots_survive_repair_without_overwriting_prior_round():
    res = result()
    res.rounds.insert(1, RoundRecord(1, 'repair', ['tests/test_double.py'], res.rounds[0].result,
                                    ['repair reply had no code block; keeping previous tests']))
    res.rounds.append(RoundRecord(3, 'repair', ['tests/test_double.py'], None))
    doc = Document(rendered(res))
    text = ''.join(doc.text)
    assert 'assert double(2) == 5' in text
    assert 'assert double(2) == 4' in text
    assert 'preceding test result was retained; no new execution was recorded' in text
    assert 'No test run was recorded for this round.' in text
    assert 'repair reply had no code block' in text


def test_timeout_and_missing_junit_do_not_present_static_count_as_verified():
    res = result()
    res.status = 'failed'
    res.final = SandboxResult(None, True, 2.1, 2, 'partial tail', generated_files=['tests/test_double.py']).to_dict()
    res.tests_written = 42
    res.rounds = []
    text = ''.join(Document(rendered(res)).text)
    assert 'JUnit report unavailable' in text
    assert 'authored-test count: 42' in text
    assert 'Generated cases passed / collectedUnavailable' in text
    assert 'TIMEOUT after 2s' in text
    assert '0 / 0' not in text


def test_no_final_result_stays_unavailable():
    res = result()
    res.status = 'model_error'
    res.final = None
    res.rounds = []
    res.test_files = {}
    res.patch = ''
    res.tests_written = 0
    text = ''.join(Document(rendered(res)).text)
    assert 'No generated-test result was recorded.' in text
    assert 'No individual test cases were recorded.' not in text
    assert 'The recorded patch is empty.' in text


def test_measured_zero_coverage_is_not_unavailable():
    res = result()
    res.coverage = {'total_before': 0.0, 'total_after': 0.0, 'total_delta': 0.0,
                    'changed_lines_executable': 4, 'changed_lines_before': 0.0, 'changed_lines_after': 0.0}
    text = ''.join(Document(rendered(res)).text)
    assert 'Coverage unavailable.' not in text
    assert 'Changed executable lines: 4' in text
    assert '0.0' in text


def test_unpriced_subtotal_and_estimated_tokens_do_not_claim_zero_cost():
    res = result()
    ledger = Ledger(RoutingConfig(prices={'P': (1.0, 2.0)}))
    ledger.record('planner', 'P', Usage(1000, 2000, False))
    ledger.record('repair', 'E', Usage(10, 20, True))
    res.ledger = ledger.to_dict()
    text = ''.join(Document(rendered(res)).text)
    assert 'Cost is unpriced or incomplete.' in text
    assert 'does not establish the full cost' in text
    assert '$0.005 USD' in text
    assert 'estimated from text length' in text
    assert 'Cost at supplied prices:' not in text


def test_no_calls_and_complete_pricing_are_separate():
    res = result()
    res.ledger = Ledger(RoutingConfig()).to_dict()
    text = ''.join(Document(rendered(res)).text)
    assert 'No model calls were recorded.' in text
    assert 'Cost at supplied prices:' not in text
    ledger = Ledger(RoutingConfig(prices={'P': (1.0, 2.0)}))
    ledger.record('planner', 'P', Usage(1000, 2000, False))
    res.ledger = ledger.to_dict()
    text = ''.join(Document(rendered(res)).text)
    assert 'Cost at supplied prices: $0.005 USD.' in text
    assert 'reported by the configured client.' in text


@pytest.mark.parametrize('status', ['passed', 'failed', 'suspected_code_bug', 'no_changes', 'no_tests',
                                   'budget_exhausted', 'model_error'])
def test_every_native_outcome_can_be_written(status, tmp_path):
    res = result()
    res.status = status
    output = write_outputs(res, tmp_path)['html'].read_text()
    assert status in ''.join(Document(output).text)
    assert output.encode('utf-8')


def test_all_free_text_is_literal_and_document_has_no_executable_content():
    res = result()
    attack = '</style><script>alert(1)</script><img src="https://example.invalid/x" onerror="alert(2)">& café 雪 🦉'
    res.message = attack
    res.plan = attack
    res.patch = attack
    res.test_files = {attack: attack}
    res.changed_functions = [{'path': attack, 'qualname': attack, 'source': attack, 'lineno': 1, 'end_lineno': 2}]
    res.final['cases'][0].update(nodeid=attack, message=attack)
    res.final['output'] = attack
    res.rounds[0].warnings = [attack]
    res.rounds[0].contents = {attack: attack}
    res.ledger['entries'][0].update(role=attack, model=attack)
    doc = Document(rendered(res))
    text = ''.join(doc.text)
    assert attack in text
    assert all(tag not in ('script', 'img', 'iframe', 'object', 'embed', 'link', 'form', 'input') for tag, _ in doc.tags)
    for tag, attrs in doc.tags:
        assert not any(key.startswith('on') for key in attrs)
        assert 'src' not in attrs
        if 'href' in attrs:
            assert attrs['href'].startswith(('#', 'data:'))
    assert doc.downloads()['testpilot.patch'] == attack.encode('utf-8')


def test_control_and_surrogate_text_is_visible_without_changing_json(tmp_path):
    res = result()
    res.message = 'literal\\udcff / raw:\udcff\x00\r\x1b / 雪 e\u0301'
    paths = write_outputs(res, tmp_path)
    doc = Document(paths['html'].read_text())
    text = ''.join(doc.text)
    assert 'raw:\\udcff\\x00\\r\\x1b' in text
    assert '雪 e\u0301' in text
    assert json.loads(doc.downloads()['report.json'])['message'] == res.message


def test_rendering_is_deterministic_and_does_not_require_source_files():
    res = result()
    assert rendered(res) == rendered(res)
    assert 'Recorded pytest output' in rendered(res)
    assert 'last 3,000 characters' in rendered(res)
