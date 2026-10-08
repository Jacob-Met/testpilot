// SPDX-License-Identifier: Apache-2.0
const $ = (id) => document.getElementById(id);
const stageNames = ['Diff inspection', 'Generated tests', 'Recorded execution', 'Ground-truth replay'];
let dataset;
let selected = 0;
let stage = 0;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function validate(data) {
  if (data.schema !== 'testpilot.offline-replay.v1' || !/^[a-f0-9]{40}$/.test(data.source?.commit) ||
      !Array.isArray(data.cases) || data.cases.length !== 2 ||
      data.execution?.backend !== 'ScriptedModel' || data.execution.live_model_calls !== 0) {
    throw new Error('The recorded dataset has an unsupported format.');
  }
  const ids = new Set();
  for (const item of data.cases) {
    if (!/^[a-z0-9_]+$/.test(item.id) || ids.has(item.id)) throw new Error('Invalid fixture identity.');
    ids.add(item.id);
    for (const name of ['baseline', 'generated', 'fixed', 'witness_buggy', 'witness_fixed']) {
      const run = item.runs?.[name];
      if (!run || !Number.isInteger(run.passed) || !Number.isInteger(run.failed) || run.errors || run.timed_out || run.skipped) {
        throw new Error('A required fixture run is incomplete.');
      }
    }
    if (!item.runs.baseline.ok || !item.runs.fixed.ok || item.runs.witness_buggy.ok || !item.runs.witness_fixed.ok ||
        (item.kind === 'caught' && (item.runs.generated.ok || item.status !== 'suspected_code_bug')) ||
        (item.kind === 'missed' && (!item.runs.generated.ok || item.status !== 'passed')) ||
        !['caught', 'missed'].includes(item.kind)) throw new Error('The recorded verdict does not match its evidence.');
    for (const file of Object.values(item.files)) {
      if (!file.url.startsWith(`data/cases/${item.id}/`) || file.url.includes('..') ||
          !/^[a-f0-9]{64}$/.test(file.sha256) || !Number.isInteger(file.bytes)) {
        throw new Error('Invalid recorded artifact.');
      }
    }
  }
  return data;
}

function codeCard(title, content, kind = 'recorded source', diff = false) {
  const card = element('div', undefined, 'code-card');
  const heading = element('div', undefined, 'code-heading');
  heading.append(element('span', title), element('span', kind, 'code-kind'));
  const pre = element('pre');
  const code = element('code');
  if (diff) {
    for (const line of content.split('\n')) {
      const color = line.startsWith('+') && !line.startsWith('+++') ? ' added' :
        line.startsWith('-') && !line.startsWith('---') ? ' removed' : line.startsWith('@@') ? ' hunk' : '';
      code.append(element('span', line || ' ', `code-line${color}`));
    }
  } else code.textContent = content;
  pre.append(code);
  card.append(heading, pre);
  return card;
}

function metrics(items) {
  const row = element('div', undefined, 'metrics');
  for (const [label, value, unit] of items) {
    const card = element('div', undefined, 'metric');
    card.append(element('span', label), element('strong', String(value)), element('small', unit));
    row.append(card);
  }
  return row;
}

function verdict(title, text, tone = '') {
  const box = element('div', undefined, `verdict ${tone}`);
  box.append(element('h3', title), element('p', text));
  return box;
}

function runCard(title, run, note) {
  const card = element('section', undefined, 'run-card');
  card.append(element('h3', title), element('div', `${run.passed} pass / ${run.failed} fail`, `run-counts${run.failed ? ' failed' : ''}`),
    element('p', `Process exit ${run.returncode}. ${note}`));
  return card;
}

function artifact(id, item, filename) {
  const a = $(id);
  a.href = item.files[filename].url;
  a.download = `${item.id}-${filename}`;
  a.removeAttribute('aria-disabled');
  a.dataset.sha256 = item.files[filename].sha256;
}

function render() {
  const item = dataset.cases[selected];
  $('case-list').replaceChildren(...dataset.cases.map((entry, index) => {
    const button = element('button', undefined, 'case-button');
    button.type = 'button';
    button.setAttribute('aria-pressed', String(index === selected));
    button.dataset.case = entry.id;
    button.append(element('span', `FIXTURE 0${index + 1}`, 'case-number'), element('strong', entry.title),
      element('small', entry.subtitle), element('span', '↗', 'case-arrow'));
    button.addEventListener('click', () => {
      selected = index; stage = 0; render();
      $('case-list').querySelector(`[data-case="${entry.id}"]`).focus();
    });
    return button;
  }));
  for (const tab of $('stages').querySelectorAll('button')) {
    const active = Number(tab.dataset.stage) === stage;
    tab.setAttribute('aria-selected', String(active));
    tab.tabIndex = active ? 0 : -1;
  }
  const panel = $('stage-content');
  panel.replaceChildren();
  panel.setAttribute('aria-labelledby', `stage-tab-${stage}`);
  const heading = element('div', undefined, 'stage-heading');
  const titles = [`A small change to ${item.function}().`, 'What the fixture asks to test.', 'Read the actual test result.', 'Does the fix satisfy the tests?'];
  heading.append(element('h2', titles[stage]), element('span', stage === 3 ? 'ORACLE CHECK' : 'RECORDED EVIDENCE', 'badge'));
  panel.append(heading);
  if (stage === 0) {
    panel.append(element('p', item.bug, 'stage-description'), metrics([
      ['EXISTING SUITE', item.runs.baseline.passed, 'pass'], ['GENERATED TESTS', item.tests_written, 'new'], ['FIXTURE', selected + 1, 'of 2'],
    ]), codeCard(item.module, item.diff, 'input diff', true),
    element('p', 'The existing suite passes on this changed implementation. The next stage shows the authored planner reply and the tests produced by the recorded pipeline.', 'context-note'));
  } else if (stage === 1) {
    panel.append(element('p', 'These are the actual authored fixture replies consumed by ScriptedModel. The pipeline runs the generated files together with the existing repository tests.', 'stage-description'));
    const plan = element('div', undefined, 'plan-card');
    plan.append(element('span', 'RECORDED PLANNER REPLY', 'section-label'), element('div', item.plan));
    panel.append(plan);
    for (const [name, content] of Object.entries(item.generated_tests)) panel.append(codeCard(name, content, 'generated test'));
    panel.append(element('p', `${item.scripted_calls} authored replies were consumed; ${item.repair_rounds} repair round${item.repair_rounds === 1 ? '' : 's'} used. No live model was called.`, 'context-note'));
  } else if (stage === 2) {
    const run = item.runs.generated;
    panel.append(element('p', item.kind === 'caught' ? 'The recorded tests expose the changed implementation. A failing assertion is useful evidence: TestPilot keeps it when the authored repair reply identifies a code bug.' : 'The generated suite passes, but the even-length regression remains outside these assertions. Continue to the independent boundary witness before treating this as a fix.', 'stage-description'));
    panel.append(verdict(item.kind === 'caught' ? 'Code bug suspected — failing assertions retained' : 'Generated suite passed — boundary still untested', item.message, item.kind === 'caught' ? 'failure' : 'warning'));
    panel.append(metrics([['PASSED', run.passed, 'tests'], ['FAILED', run.failed, 'tests'], ['PROCESS EXIT', run.returncode, 'recorded']]));
    panel.append(codeCard('pytest / generated tests', run.output, 'output excerpt'));
  } else {
    panel.append(element('p', item.explanation, 'stage-description'));
    const comparison = element('div', undefined, 'compare-grid');
    comparison.append(runCard('Generated tests · changed code', item.runs.generated, 'Same generated assertions.'),
      runCard('Generated tests · oracle fix', item.runs.fixed, 'Ground-truth source substituted.'));
    panel.append(comparison, verdict(item.kind === 'caught' ? 'The regression distinguishes the buggy and fixed code.' : 'Green generated tests missed this regression.', item.kind === 'caught' ? 'The tests fail before the ground-truth fix and pass after it. The fixture oracle was never shown to ScriptedModel.' : 'An independently authored even-length witness exposes the missed bug. It is separate from the generated patch and was never supplied to ScriptedModel.', item.kind === 'caught' ? '' : 'warning'));
    const witness = element('div', undefined, 'compare-grid');
    witness.append(runCard('Boundary witness · changed code', item.runs.witness_buggy, 'Independent authored control.'),
      runCard('Boundary witness · oracle fix', item.runs.witness_fixed, 'Identical boundary assertion.'));
    panel.append(witness, codeCard('independent boundary witness', item.witness, 'authored control'));
    const details = element('details', undefined, 'run-details');
    details.append(element('summary', 'Inspect the ground-truth source and passing output'), codeCard(item.module, item.oracle, 'fixture oracle'), codeCard('pytest / oracle-fixed source', item.runs.fixed.output, 'output excerpt'));
    panel.append(details);
  }
  artifact('download-patch', item, 'testpilot.patch');
  artifact('download-record', item, 'record.json');
  artifact('download-log', item, 'generated.log');
  $('previous').disabled = stage === 0;
  $('next').disabled = false;
  $('next').textContent = ['Inspect tests →', 'Read recorded run →', 'Check oracle →', 'Start over ↻'][stage];
  $('step-count').textContent = `Step ${stage + 1} of 4`;
  $('case-position').textContent = item.id;
  $('announcement').textContent = `${item.title}. ${stageNames[stage]}. Step ${stage + 1} of 4.`;
  const url = new URL(location.href);
  url.searchParams.set('case', item.id);
  url.searchParams.set('stage', String(stage + 1));
  history.replaceState(null, '', url);
}

$('stages').addEventListener('click', (event) => {
  const tab = event.target.closest('button[data-stage]');
  if (!dataset || !tab) return;
  stage = Number(tab.dataset.stage);
  render();
});
$('stages').addEventListener('keydown', (event) => {
  if (!dataset || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  stage = event.key === 'Home' ? 0 : event.key === 'End' ? 3 : (stage + (event.key === 'ArrowRight' ? 1 : 3)) % 4;
  render();
  $(`stage-tab-${stage}`).focus();
});
$('previous').addEventListener('click', () => { if (dataset && stage > 0) { stage--; render(); } });
$('next').addEventListener('click', () => { if (dataset) { stage = (stage + 1) % 4; render(); } });

try {
  const response = await fetch('data/replays.json');
  if (!response.ok) throw new Error(`Recorded evidence could not be loaded (${response.status}).`);
  dataset = validate(await response.json());
  const params = new URL(location.href).searchParams;
  selected = Math.max(0, dataset.cases.findIndex((item) => item.id === params.get('case')));
  const requestedStage = Number(params.get('stage'));
  stage = Number.isInteger(requestedStage) && requestedStage >= 1 && requestedStage <= 4 ? requestedStage - 1 : 0;
  $('source-link').href = `https://github.com/Jacob-Met/testpilot/commit/${dataset.source.commit}`;
  $('source-link').textContent = dataset.source.commit.slice(0, 12);
  $('runtime').textContent = `Python ${dataset.execution.python} · pytest ${dataset.execution.pytest}`;
  $('recorded-at').textContent = new Date(dataset.recorded_at).toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  render();
  $('replay').setAttribute('aria-busy', 'false');
} catch (error) {
  $('replay').hidden = true;
  $('load-error').hidden = false;
  $('load-error').textContent = `${error.message} Serve the web-demo directory with “python3 -m http.server 8000” and open http://localhost:8000. This page requires its recorded data files.`;
}
