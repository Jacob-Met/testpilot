"""A self-contained, script-free review of the already serialized run artifacts.

This is an output renderer, not a report importer, runner, or verifier. Embedded
downloads retain the exact bytes supplied by write_outputs, including native
newline handling. Visible text escapes controls/surrogates that HTML cannot
represent faithfully; the JSON and patch downloads remain unchanged.
"""
from __future__ import annotations

import base64
import html
import json
import unicodedata


_STYLE = """
:root { color-scheme: light; --ink:#192d3b; --muted:#50616d; --line:#cbd5dc;
  --paper:#fff; --wash:#f3f6f7; --accent:#155d68; --soft:#e8f2f1; }
* { box-sizing:border-box; }
html { scroll-padding-top:1.5rem; }
body { margin:0; color:var(--ink); background:var(--wash);
  font:16px/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
a { color:var(--accent); text-underline-offset:.2em; }
a:hover { text-decoration-thickness:2px; }
:focus-visible { outline:3px solid #aa5e00; outline-offset:4px; }
.skip { position:absolute; top:-100px; left:1rem; background:white; padding:.6rem; }
.skip:focus { top:1rem; z-index:1; }
.shell { width:min(1120px,100%); margin:auto; padding:2.5rem 2rem 3.5rem; }
.eyebrow { margin:0 0 .7rem; color:var(--accent); font-size:.8rem;
  font-weight:750; letter-spacing:.15em; text-transform:uppercase; }
h1 { font-size:clamp(2rem,5vw,3.25rem); line-height:1.1; margin:.2rem 0 1rem; }
h2 { font-size:1.4rem; line-height:1.3; margin:0 0 1rem; }
h3 { font-size:1.08rem; margin:1.4rem 0 .7rem; }
p { margin:.7rem 0; }
.lead { font-size:1.1rem; max-width:78ch; }
.muted,.note { color:var(--muted); }
.note { font-size:.9rem; }
.status { display:inline-block; padding:.18rem .7rem; margin-bottom:.5rem;
  border:1px solid var(--line); border-radius:999px; font-weight:700; }
.passed { background:#e7f3ed; color:#175137; }
.failed,.error { background:#fceeed; color:#882e24; }
.suspected_code_bug,.budget_exhausted,.model_error,.no_tests { background:#fff0d6; color:#6c4509; }
.actions { display:flex; gap:.7rem; flex-wrap:wrap; margin:1.4rem 0 .6rem; }
.button { display:inline-block; padding:.65rem 1rem; border:1px solid var(--accent);
  border-radius:.35rem; background:var(--paper); font-weight:650; text-decoration:none; }
.button.primary { background:var(--accent); color:white; }
nav { display:flex; gap:.6rem 1.2rem; flex-wrap:wrap; padding:1rem 0;
  border-top:1px solid var(--line); border-bottom:1px solid var(--line); margin:1.8rem 0; }
.metrics { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.8rem; margin:1.4rem 0; }
.metric { background:var(--paper); border:1px solid var(--line); border-radius:.4rem; padding:1rem; }
.metric dt { font-size:.85rem; color:var(--muted); }
.metric dd { margin:0; font-weight:700; font-size:1.35rem; overflow-wrap:anywhere; }
section { background:var(--paper); border:1px solid var(--line); border-radius:.5rem;
  padding:1.5rem; margin:1.2rem 0; min-width:0; }
.notice { border-left:4px solid var(--accent); background:var(--soft); padding:.7rem 1rem; }
details { border:1px solid var(--line); border-radius:.35rem; margin:.65rem 0; min-width:0; }
summary { padding:.75rem 1rem; cursor:pointer; font-weight:600; overflow-wrap:anywhere; }
details[open] > summary { border-bottom:1px solid var(--line); background:var(--wash); }
.detail-body { padding:.25rem 1rem .8rem; min-width:0; }
.badge { display:inline-block; font-size:.76rem; margin-right:.4rem; padding:.05rem .4rem;
  border:1px solid var(--line); border-radius:.2rem; font-weight:650; }
code,pre { font-family:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace; }
code { overflow-wrap:anywhere; }
pre { margin:.6rem 0; padding:1rem; border:1px solid var(--line); border-radius:.3rem;
  background:#f7f9fa; line-height:1.5; font-size:.86rem; overflow:auto; max-width:100%;
  tab-size:4; white-space:pre; }
.prose { white-space:pre-wrap; overflow-wrap:anywhere; }
.table-scroll { overflow-x:auto; max-width:100%; }
table { width:100%; min-width:24rem; border-collapse:collapse; text-align:left; font-size:.9rem; }
table.wide { min-width:46rem; }
th,td { border-bottom:1px solid var(--line); padding:.6rem .7rem; vertical-align:top; overflow-wrap:anywhere; }
th { color:var(--muted); font-weight:650; white-space:nowrap; }
caption { text-align:left; padding:.3rem 0 .7rem; color:var(--muted); }
.table-hint { display:none; }
ol,ul { padding-left:1.4rem; }
.cases { list-style:none; padding:0; }
.case-label { color:var(--muted); font-size:.8rem; font-weight:400; }
.rounds { padding-left:1.4rem; }
.rounds > li { padding-left:.3rem; margin:1rem 0; }
footer { margin-top:2rem; font-size:.9rem; color:var(--muted); }
@media(max-width:620px) {
  .shell { padding:1.5rem .8rem 2rem; }
  section { padding:1rem; }
  .metrics { grid-template-columns:1fr; gap:.5rem; }
  .metric { display:flex; align-items:baseline; justify-content:space-between; gap:1rem; padding:.65rem .8rem; }
  .metric dd { font-size:1.1rem; }
  summary { padding:.65rem .7rem; }
  .detail-body { padding:.2rem .7rem .6rem; }
  .table-hint { display:block; margin:.3rem 0 .7rem; }
}
@media print {
  body { background:white; font-size:10pt; }
  .shell { width:100%; padding:0; }
  nav,.actions,.skip,.download-note { display:none; }
  section,details,.metric { border-color:#aaa; box-shadow:none; }
  section { break-inside:auto; }
  h2,h3,summary { break-after:avoid; }
  pre { white-space:pre-wrap; overflow-wrap:anywhere; overflow:visible; }
  .table-scroll { overflow:visible; }
  table,table.wide { min-width:0; font-size:8pt; }
  th { white-space:normal; }
  .table-hint { display:none; }
  details::details-content { content-visibility:visible; }
  details > :not(summary) { display:block !important; }
  .metrics { grid-template-columns:repeat(3,minmax(0,1fr)); }
}
"""

_STATUS = {
    "passed": ("Passed", "The runner reported a passing selected suite. Passing tests do not establish that the changed code is correct."),
    "failed": ("Needs review", "The run did not qualify as passing. Inspect the recorded test results and diagnostics."),
    "suspected_code_bug": ("Possible code bug", "The model flagged a possible code bug. Review its explanation and the retained failing tests."),
    "no_changes": ("No selected changes", "No changed Python functions were selected for this run."),
    "no_tests": ("No qualified generated tests", "No generated test case qualified as passing."),
    "budget_exhausted": ("Token budget reached", "The run stopped at its configured token budget. Any earlier recorded results remain below."),
    "model_error": ("Model request failed", "A model request failed. Any earlier recorded results remain below."),
}


def _text(value: object) -> str:
    value = "—" if value is None else str(value)
    visible = "".join(
        ch.encode("unicode_escape").decode("ascii")
        if (0xD800 <= ord(ch) <= 0xDFFF
            or (unicodedata.category(ch) == "Cc" and ch not in "\n\t")) else ch
        for ch in value
    )
    return html.escape(visible, quote=True)


def _pre(value: object) -> str:
    return '<pre tabindex="0"><code>' + _text(value) + '</code></pre>'


def _disclosure(title: str, body: str, *, opened: bool = False) -> str:
    return ('<details' + (' open' if opened else '') + '><summary>' + title
            + '</summary><div class="detail-body">' + body + '</div></details>')


def _table(headers: list[str], rows: list[list[object]], caption: str = "") -> str:
    return ('<div class="table-scroll" tabindex="0" role="region" aria-label="'
            + _text(caption or 'Data table') + '"><table' + (' class="wide"' if len(headers) > 5 else '') + '>'
            + ('<caption>' + _text(caption) + '</caption>' if caption else '')
            + '<thead><tr>' + ''.join('<th scope="col">' + _text(x) + '</th>' for x in headers)
            + '</tr></thead><tbody>'
            + ''.join('<tr>' + ''.join('<td>' + _text(x) + '</td>' for x in row) + '</tr>' for row in rows)
            + '</tbody></table></div><p class="note table-hint">Scroll the table horizontally to read all columns.</p>')


def _files(files: dict[str, str]) -> str:
    if not files:
        return '<p class="muted">No file contents were recorded here.</p>'
    return ''.join(_disclosure('<code>' + _text(path) + '</code>', _pre(content))
                   for path, content in sorted(files.items()))


def _run(result: dict | None) -> str:
    if result is None:
        return '<p class="notice">No generated-test result was recorded.</p>'
    parts = ['<p class="prose"><strong>' + _text(result.get('summary')) + '</strong></p>']
    parts.append('<p class="note">Return code: ' + _text(result.get('returncode'))
                 + ' · Duration: ' + _text(result.get('duration_s')) + ' s'
                 + ' · Timeout: ' + ('yes' if result.get('timed_out') else 'no') + '</p>')
    if not result.get('junit_available'):
        parts.append('<p class="notice">JUnit report unavailable. Recorded counts do not establish complete '
                     'test execution; the authored-test count may be a static definition count.</p>')
    parts.append(_table(['Passed', 'Failed', 'Errors', 'Skipped'],
                        [[result.get(k) for k in ('passed', 'failed', 'errors', 'skipped')]],
                        'Recorded selected-suite case counts'))
    generated = result.get('generated')
    if generated is not None:
        parts.append(_table(['Collected', 'Passed', 'Failed', 'Errors', 'Skipped'],
                            [[generated.get(k) for k in ('collected', 'passed', 'failed', 'error', 'skipped')]],
                            'Recorded generated-case counts'))
    else:
        parts.append('<p class="note">Separate generated-case counts are unavailable.</p>')
    cases = result.get('cases', [])
    if cases:
        generated_files = set(result.get('generated_files', []))
        parts.append('<h3>Recorded test cases</h3><ol class="cases">')
        for case in cases:
            outcome = case.get('outcome', 'unknown')
            style = outcome if outcome in ('passed', 'failed', 'error') else ''
            label = 'Generated test' if case.get('generated_file') in generated_files else 'Other selected test'
            title = ('<span class="badge ' + style + '">' + _text(outcome) + '</span> '
                     '<code>' + _text(case.get('nodeid')) + '</code> '
                     '<span class="case-label">' + label + '</span>')
            body = _pre(case['message']) if case.get('message') else '<p class="note">No diagnostic message recorded.</p>'
            parts.append('<li>' + _disclosure(title, body, opened=outcome in ('failed', 'error')) + '</li>')
        parts.append('</ol>')
    else:
        parts.append('<p class="muted">No individual test cases were recorded.</p>')
    parts.append(_disclosure('Recorded pytest output',
                            '<p class="note">The runner retains the last 3,000 characters in its report. '
                            'This is the recorded tail, not a complete process log.</p>'
                            + _pre(result.get('output', ''))))
    return ''.join(parts)


def _rounds(rounds: list[dict]) -> str:
    if not rounds:
        return '<p class="muted">No generation or repair rounds were recorded.</p>'
    parts = ['<ol class="rounds">']
    for record in rounds:
        title = 'Round ' + _text(record.get('round')) + ' · ' + _text(record.get('kind'))
        body = ''
        if record.get('warnings'):
            body += '<h3>Recorded warnings</h3><ul>' + ''.join(
                '<li class="prose">' + _text(w) + '</li>' for w in record['warnings']) + '</ul>'
        if record.get('contents'):
            body += '<h3>Tests at this round</h3>' + _files(record['contents'])
        else:
            body += '<p class="note">No new test-source snapshot was recorded for this round.</p>'
            if record.get('files'):
                body += '<p>Retained file names: ' + ', '.join('<code>' + _text(p) + '</code>' for p in record['files']) + '</p>'
        if record.get('result') is None:
            body += '<p class="notice">No test run was recorded for this round.</p>'
        else:
            if not record.get('contents'):
                body += '<p class="notice">The preceding test result was retained; no new execution was recorded.</p>'
            body += _run(record['result'])
        parts.append('<li>' + _disclosure(title, body) + '</li>')
    return ''.join(parts) + '</ol>'


def render_html_report(report_json: bytes, patch: bytes) -> str:
    """Render the writer's current report JSON and exact patch as offline HTML.

    The caller supplies the artifacts just written from the same LoopResult.
    This function reads no paths, calls no model, and executes no source text.
    """
    report = json.loads(report_json)
    status = report['status']
    title, explanation = _STATUS.get(status, ('Recorded outcome', 'Inspect the recorded result below.'))
    status_class = status if status in _STATUS else ''
    final = report.get('final')
    ledger = report['ledger']
    token_note = 'estimated' if ledger['tokens_estimated'] else 'reported'
    generated = final.get('generated') if final else None
    verified_counts = bool(final and final.get('junit_available') and generated is not None)
    generated_metric = (str(generated['passed']) + ' / ' + str(generated['collected'])) if verified_counts else 'Unavailable'
    patch_uri = 'data:text/plain;charset=utf-8;base64,' + base64.b64encode(patch).decode('ascii')
    json_uri = 'data:application/json;base64,' + base64.b64encode(report_json).decode('ascii')
    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width, initial-scale=1">'
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
             'style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
             '<title>TestPilot run review · ' + _text(status) + '</title><style>' + _STYLE + '</style></head><body>'
             '<a class="skip" href="#result">Skip to test results</a><main class="shell">'
             '<header><p class="eyebrow">TestPilot / Run review</p><h1>' + _text(title) + '</h1>'
             '<span class="status ' + status_class + '">' + _text(status) + '</span>'
             '<p class="lead">' + explanation + '</p>']
    if report.get('message'):
        parts.append('<div class="notice"><p class="prose">' + _text(report['message']) + '</p></div>')
    pytest_selection = report.get('pytest_selection')
    if pytest_selection is not None:
        parts.append('<div class="notice"><h2>Pytest execution selection</h2>'
                     '<p>These native filters are configured for baseline, generation and every repair. '
                     '<strong>Unselected tests were not verified.</strong> '
                     'Saved-test recheck does not inherit these filters.</p>'
                     + _table(['Native filter', 'Literal expression (JSON)'], [
                         ['Keyword (-k)', json.dumps(pytest_selection.get('keyword'), ensure_ascii=True)],
                         ['Marker (-m)', json.dumps(pytest_selection.get('marker'), ensure_ascii=True)]])
                     + '</div>')
    parts.append('<div class="actions"><a class="button primary" download="testpilot.patch" href="' + patch_uri
                 + '">Download exact patch</a><a class="button" download="report.json" href="' + json_uri
                 + '">Download report JSON</a></div>'
                 '<p class="note download-note">Both downloads are embedded in this file. Opening, reviewing or '
                 'downloading does not run tests or apply the patch.</p></header>')
    parts.append('<dl class="metrics"><div class="metric"><dt>Generated cases passed / collected</dt><dd>'
                 + _text(generated_metric) + '</dd></div><div class="metric"><dt>Repair rounds used / limit</dt><dd>'
                 + _text(report['repair_rounds_used']) + ' / ' + _text(report['max_repair_rounds'])
                 + '</dd></div><div class="metric"><dt>Tokens · ' + token_note + '</dt><dd>'
                 + _text(ledger['total_tokens']) + '</dd></div></dl>')
    parts.append('<nav aria-label="Report sections">' + ''.join(
        '<a href="#' + key + '">' + name + '</a>' for key, name in
        [('result', 'Test results'), ('tests', 'Generated files'), ('rounds', 'Repair history'),
         ('scope', 'Plan and scope'), ('coverage', 'Coverage'), ('ledger', 'Model ledger'), ('patch', 'Patch')]) + '</nav>')
    parts.append('<section id="result" aria-labelledby="result-heading"><h2 id="result-heading">Final recorded result</h2>'
                 + _run(final) + '</section>')
    parts.append('<section id="tests" aria-labelledby="tests-heading"><h2 id="tests-heading">Final generated files</h2>'
                 '<p class="note">Reported authored-test count: ' + _text(report['tests_written'])
                 + '. This count is separate from verified generated-case execution above.</p>'
                 + _files(report['test_files']) + '</section>')
    parts.append('<section id="rounds" aria-labelledby="rounds-heading"><h2 id="rounds-heading">Repair history</h2>'
                 '<p class="note">Each round keeps its recorded source snapshot and result. '
                 'A model response without a new run does not add an execution.</p>'
                 + _rounds(report['rounds']) + '</section>')
    parts.append('<section id="scope" aria-labelledby="scope-heading"><h2 id="scope-heading">Plan and selected source</h2>')
    selection = report.get("selection")
    if isinstance(selection, dict) and selection.get("mode") == "explicit":
        parts.append('<p class="notice">' + _text(selection.get("reason", "Caller-selected targets.")) + '</p>')
        parts.append(_disclosure("Supplied diff context", _pre(selection.get("diff_text", ""))))
    if report.get('plan'):
        parts.append('<h3>Model test plan</h3>' + _pre(report['plan']))
    else:
        parts.append('<p class="muted">No model test plan was recorded.</p>')
    for fn in report['changed_functions']:
        heading = ('<code>' + _text(fn['path']) + '::' + _text(fn['qualname']) + '</code> '
                   '<span class="case-label">lines ' + _text(fn.get('lineno')) + '–' + _text(fn.get('end_lineno')) + '</span>')
        parts.append(_disclosure(heading, _pre(fn.get('source', ''))))
    if not report['changed_functions']:
        parts.append('<p class="muted">No changed functions were selected.</p>')
    parts.append('</section><section id="coverage" aria-labelledby="coverage-heading"><h2 id="coverage-heading">Coverage</h2>')
    coverage = report.get('coverage')
    if coverage is None:
        parts.append('<p class="notice">Coverage unavailable. This report contains no comparable before/after measurement.</p>')
    else:
        parts.append(_table(['Measurement', 'Before', 'After'], [
            ['Total coverage (%)', coverage.get('total_before'), coverage.get('total_after')],
            ['Changed executable lines (%)', coverage.get('changed_lines_before'), coverage.get('changed_lines_after')]],
            'Recorded coverage comparison'))
        parts.append('<p class="note">Total change: ' + _text(coverage.get('total_delta'))
                     + ' percentage points · Changed executable lines: ' + _text(coverage.get('changed_lines_executable'))
                     + '. Coverage measures executed lines, not assertion quality.</p>')
    parts.append('</section><section id="ledger" aria-labelledby="ledger-heading"><h2 id="ledger-heading">Model and token ledger</h2>')
    if not ledger.get('entries'):
        parts.append('<p class="notice">No model calls were recorded.</p>')
    else:
        parts.append('<p>Token counts are ' + ('estimated from text length.' if ledger['tokens_estimated']
                     else 'reported by the configured client.') + '</p>')
        if ledger['cost_is_complete']:
            parts.append('<p>Cost at supplied prices: $' + _text(ledger['total_cost_usd']) + ' USD.</p>')
        else:
            parts.append('<p class="notice">Cost is unpriced or incomplete. The recorded subtotal ($'
                         + _text(ledger['total_cost_usd']) + ' USD) does not establish the full cost.</p>')
        parts.append(_table(['Call', 'Role', 'Model', 'Prompt tokens', 'Completion tokens', 'Token source', 'Recorded cost (USD)'],
                            [[i + 1, e['role'], e['model'], e['prompt_tokens'], e['completion_tokens'],
                              'estimated' if e['estimated'] else 'reported', e['cost_usd']]
                             for i, e in enumerate(ledger['entries'])], 'Calls in recorded order'))
    parts.append('</section><section id="patch" aria-labelledby="patch-heading"><h2 id="patch-heading">Exact recorded patch</h2>')
    if report['patch']:
        parts.append(_pre(report['patch']))
    else:
        parts.append('<p class="muted">The recorded patch is empty.</p>')
    parts.append('</section><footer><p>This file reviews the recorded TestPilot result. It does not rerun '
                 'the repository, verify a model diagnosis, or change any source. Text is displayed literally; '
                 'HTML-incompatible controls and surrogate characters use visible escapes. Embedded downloads '
                 'retain the original artifact bytes.</p><p>Use your browser’s Print command to print the report. '
                 'No scripts, remote resources, storage or account are required.</p></footer></main></body></html>\n')
    return ''.join(parts)
