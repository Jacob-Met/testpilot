"""Phase notices preserve delegated work, failure semantics and accounting."""
import io
from pathlib import Path

import pytest

from testpilot.loop import BudgetExceeded, Ledger, TestPilot
from testpilot.model import RoutingConfig, ScriptedModel, ScriptExhausted
from testpilot.progress import ProgressTestPilot
from testpilot.sandbox import CaseResult, SandboxResult


def test_actual_scripted_model_accounting_and_sensitive_text_stay_unchanged(monkeypatch):
    stream = io.StringIO()
    monkeypatch.setattr('sys.stderr', stream)
    routing = RoutingConfig()
    model = ScriptedModel(['PRIVATE-RESPONSE'])
    pilot = ProgressTestPilot(model, routing)
    ledger = Ledger(routing)
    reply = pilot._ask(ledger, 'planner', 'PRIVATE-SYSTEM', 'PRIVATE-PROMPT')
    assert reply == 'PRIVATE-RESPONSE'
    assert len(model.calls) == 1
    assert len(ledger.entries) == 1
    assert ledger.total_tokens > 0
    assert stream.getvalue() == ('[testpilot] Planning tests: starting\n'
                                 '[testpilot] Planning tests: completed\n')


def test_budget_refusal_does_not_claim_model_completion_or_make_a_call(monkeypatch):
    stream = io.StringIO()
    monkeypatch.setattr('sys.stderr', stream)
    model = ScriptedModel(['unused'])
    routing = RoutingConfig()
    pilot = ProgressTestPilot(model, routing)
    ledger = Ledger(routing, max_total_tokens=0)
    with pytest.raises(BudgetExceeded):
        pilot._ask(ledger, 'editor', 'system', 'user')
    assert model.calls == []
    assert ledger.entries == []
    assert stream.getvalue() == '[testpilot] Generating tests: starting\n'


def test_absent_stderr_disables_progress_without_falling_back_to_stdout(monkeypatch):
    normal_output = io.StringIO()
    monkeypatch.setattr('sys.stderr', None)
    monkeypatch.setattr('sys.stdout', normal_output)
    model = ScriptedModel(['one', 'two'])
    pilot = ProgressTestPilot(model)
    ledger = Ledger(pilot.routing)
    assert pilot._ask(ledger, 'planner', '', '') == 'one'
    assert pilot._ask(ledger, 'editor', '', '') == 'two'
    assert normal_output.getvalue() == ''
    assert len(model.calls) == len(ledger.entries) == 2


def test_model_error_preserves_exception_and_has_no_completion_line(monkeypatch):
    stream = io.StringIO()
    monkeypatch.setattr('sys.stderr', stream)
    model = ScriptedModel([])
    pilot = ProgressTestPilot(model)
    with pytest.raises(ScriptExhausted):
        pilot._ask(Ledger(pilot.routing), 'repair', 'system', 'user')
    assert len(model.calls) == 1
    assert stream.getvalue() == '[testpilot] Repairing tests: starting\n'


@pytest.mark.parametrize('files,phase', [(None, 'Baseline pytest'), ({}, 'Generated pytest')])
@pytest.mark.parametrize('kind', ['counts', 'timeout', 'no_junit'])
def test_native_result_identity_and_qualification_are_retained(monkeypatch, files, phase, kind):
    stream = io.StringIO()
    monkeypatch.setattr('sys.stderr', stream)
    result = SandboxResult(1, kind == 'timeout', 0.1, 1.0, 'PRIVATE-NATIVE-OUTPUT',
                           cases=[CaseResult('a', 'passed'), CaseResult('b', 'failed'),
                                  CaseResult('c', 'error'), CaseResult('d', 'skipped')],
                           junit_available=kind == 'counts')
    calls = []
    def run(pilot, repo, received):
        calls.append((repo, received))
        return result
    monkeypatch.setattr(TestPilot, '_run', run)
    repo = Path('/PRIVATE-PROJECT')
    pilot = ProgressTestPilot(ScriptedModel([]))
    assert pilot._run(repo, files) is result
    assert calls == [(repo, files)]
    detail = {'counts': 'finished: 1 passed, 1 failed, 1 errors, 1 skipped (rc=1)',
              'timeout': 'timed out',
              'no_junit': 'finished without usable JUnit (rc=1)'}[kind]
    assert stream.getvalue() == f'[testpilot] {phase}: running\n[testpilot] {phase}: {detail}\n'


class BrokenStream:
    def __init__(self, failure, error):
        self.failure, self.error = failure, error
        self.writes = self.flushes = self.closes = 0

    def write(self, text):
        self.writes += 1
        if self.failure == 'write':
            raise self.error
        return len(text)

    def flush(self):
        self.flushes += 1
        if self.failure == 'flush':
            raise self.error

    def close(self):
        self.closes += 1
        raise OSError('close also failed')


@pytest.mark.parametrize('failure', ['write', 'flush'])
@pytest.mark.parametrize('error', [BrokenPipeError(), UnicodeError(), ValueError('closed')])
def test_optional_sink_failure_does_not_abort_or_repeat_work(monkeypatch, failure, error):
    stream = BrokenStream(failure, error)
    monkeypatch.setattr('sys.stderr', stream)
    model = ScriptedModel(['one', 'two'])
    pilot = ProgressTestPilot(model)
    ledger = Ledger(pilot.routing)
    assert pilot._ask(ledger, 'planner', '', '') == 'one'
    after_first = (stream.writes, stream.flushes, stream.closes)
    assert pilot._ask(ledger, 'editor', '', '') == 'two'
    assert (stream.writes, stream.flushes, stream.closes) == after_first
    assert stream.closes == 1
    assert len(model.calls) == len(ledger.entries) == 2


@pytest.mark.parametrize('kind', ['ask', 'run'])
def test_caller_cancellation_propagates_from_delegated_operation(monkeypatch, kind):
    stream = io.StringIO()
    monkeypatch.setattr('sys.stderr', stream)
    interruption = KeyboardInterrupt()
    calls = []
    def interrupted(*args):
        calls.append(args)
        raise interruption
    monkeypatch.setattr(TestPilot, '_' + kind, interrupted)
    pilot = ProgressTestPilot(ScriptedModel([]))
    with pytest.raises(KeyboardInterrupt) as caught:
        if kind == 'ask':
            pilot._ask(Ledger(pilot.routing), 'planner', '', '')
        else:
            pilot._run(Path('/project'), None)
    assert caught.value is interruption
    assert len(calls) == 1
    assert len(stream.getvalue().splitlines()) == 1
