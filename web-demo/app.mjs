// SPDX-License-Identifier: Apache-2.0
const $ = (id) => document.getElementById(id);
const stageNames = ['Diff inspection', 'Generated tests', 'Recorded execution', 'Ground-truth replay'];
const stageTitles = (item) => [`A small change to ${item.function}().`, 'What the fixture asks to test.', 'Read the actual test result.', 'Does the fix satisfy the tests?'];
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

// One diff line becomes a gutter marker plus text, so adds and removes read at a glance.
function diffRow(line) {
  if (line.startsWith('@@')) return ['hunk', '', line];
  if (line.startsWith('+++') || line.startsWith('---') || /^(diff |index )/.test(line)) return ['meta', '', line];
  if (line.startsWith('+')) return ['add', '+', line.slice(1)];
  if (line.startsWith('-')) return ['remove', '-', line.slice(1)];
  return ['context', ' ', line.startsWith(' ') ? line.slice(1) : line];
}

function codeCard(title, content, kind = 'recorded source', diff = false) {
  const card = element('div', undefined, 'code-card');
  const heading = element('div', undefined, 'code-heading');
  heading.append(element('span', title), element('span', kind, 'code-kind'));
  const pre = element('pre', undefined, diff ? 'diff' : undefined);
  const code = element('code');
  if (diff) {
    for (const line of content.split('\n')) {
      const [kindName, gutter, text] = diffRow(line);
      const row = element('span', undefined, `code-line ${kindName}`);
      row.append(element('span', gutter || ' ', 'gutter'), element('span', text || ' ', 'code-text'));
      code.append(row);
    }
  } else code.textContent = content;
  pre.append(code);
  card.append(heading, pre);
  return card;
}

function metrics(items) {
  const row = element('div', undefined, 'diff-stats');
  for (const [label, value, unit] of items) {
    const span = element('span', label);
    span.append(element('strong', String(value)), document.createTextNode(` ${unit}`));
    row.append(span);
  }
  return row;
}

function verdict(title, text, tone = '') {
  const box = element('div', undefined, `verdict-box ${tone}`);
  box.append(element('h3', title), element('p', text));
  return box;
}

function runCard(title, run, note) {
  const card = element('section', undefined, 'run-card');
  card.append(element('h3', title), element('span', `${run.passed} pass / ${run.failed} fail`, `run-counts${run.failed ? ' failed' : ''}`),
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

// The headline verdict is the recorded outcome of the fixture, stated before any stage is opened.
function headline(item) {
  return item.kind === 'caught'
    ? { text: `Bug found in ${item.module}: ${item.bug}.`, tone: 'failure', kicker: `${item.title} · ${item.subtitle}` }
    : { text: `Tests pass, but the regression remains in ${item.module}: ${item.bug}.`, tone: 'warning', kicker: `${item.title} · ${item.subtitle}` };
}

function column(label, className, nodes, enter = true) {
  const col = element('section', undefined, `col ${className}${enter ? ' enter' : ''}`);
  col.append(element('h3', label, 'col-label'), ...nodes);
  return col;
}

function diffColumn(item, enter) {
  return column('Input diff', 'col-diff', [
    codeCard(item.module, item.diff, 'input diff', true),
    metrics([['existing suite', item.runs.baseline.passed, 'pass'], ['generated', item.tests_written, 'new tests']]),
  ], enter);
}

function testsColumn(item, enter, withWitness) {
  const plan = element('div', undefined, 'plan');
  plan.append(element('span', 'Recorded planner reply', 'plan-label'), element('div', item.plan, 'plan-body'));
  const nodes = [plan];
  for (const [name, content] of Object.entries(item.generated_tests)) nodes.push(codeCard(name, content, 'generated test'));
  if (withWitness) nodes.push(codeCard('independent boundary witness', item.witness, 'authored control'));
  nodes.push(element('p', `${item.scripted_calls} authored replies were consumed; ${item.repair_rounds} repair round${item.repair_rounds === 1 ? '' : 's'} used. No live model was called.`, 'context-note'));
  return column('Generated tests', 'col-tests', nodes, enter);
}

function pendingColumn(label, className, text) {
  return column(label, `${className} pending`, [element('p', text, 'pending')], false);
}

function timeline(steps) {
  const list = element('ol', undefined, 'timeline');
  for (const step of steps) {
    const li = element('li', undefined, step.tone || '');
    li.append(element('strong', step.title, step.cls || ''), element('span', step.detail, 'detail'));
    list.append(li);
  }
  return list;
}

function runsColumn(item, stage, enter) {
  const run = item.runs.generated;
  const headlineText = item.kind === 'caught' ? 'Code bug suspected — failing assertions retained' : 'Generated suite passed — boundary still untested';
  if (stage === 2) {
    return column('Run and repairs', 'col-run', [
      timeline([
        { title: 'Existing suite on changed code', detail: `${item.runs.baseline.passed} pass / ${item.runs.baseline.failed} fail`, tone: item.runs.baseline.failed ? 'fail' : 'pass' },
        { title: 'Generated tests', detail: `${run.passed} pass / ${run.failed} fail · process exit ${run.returncode}`, tone: run.failed ? 'fail' : 'pass' },
        { title: 'Repair reply', detail: `${item.repair_rounds} round${item.repair_rounds === 1 ? '' : 's'} · ${item.scripted_calls} authored replies`, tone: '' },
        { title: headlineText, detail: item.message, tone: item.kind === 'caught' ? 'fail verdict-step' : 'warn verdict-step', cls: 'verdict-title' },
      ]),
      codeCard('pytest / generated tests', run.output, 'output excerpt'),
    ], enter);
  }
  const compare = element('div', undefined, 'run-grid');
  compare.append(runCard('Generated tests · changed code', item.runs.generated, 'Same generated assertions.'),
    runCard('Generated tests · oracle fix', item.runs.fixed, 'Ground-truth source substituted.'),
    runCard('Boundary witness · changed code', item.runs.witness_buggy, 'Independent authored control.'),
    runCard('Boundary witness · oracle fix', item.runs.witness_fixed, 'Identical boundary assertion.'));
  const details = element('details', undefined, 'run-details');
  details.append(element('summary', 'Inspect the ground-truth source and passing output'), codeCard(item.module, item.oracle, 'fixture oracle'), codeCard('pytest / oracle-fixed source', item.runs.fixed.output, 'output excerpt'));
  return column('Oracle check', 'col-run', [
    compare,
    verdict(item.kind === 'caught' ? 'The regression distinguishes the buggy and fixed code.' : 'Green generated tests missed this regression.', item.kind === 'caught' ? 'The tests fail before the ground-truth fix and pass after it. The fixture oracle was never shown to ScriptedModel.' : 'An independently authored even-length witness exposes the missed bug. It is separate from the generated patch and was never supplied to ScriptedModel.', item.kind === 'caught' ? '' : 'warning'),
    details,
  ], enter);
}

function render() {
  const item = dataset.cases[selected];
  $('case-list').replaceChildren(...dataset.cases.map((entry, index) => {
    const button = element('button', undefined, 'case-button');
    button.type = 'button';
    button.setAttribute('aria-pressed', String(index === selected));
    button.dataset.case = entry.id;
    button.append(element('strong', entry.title), element('small', entry.subtitle));
    button.addEventListener('click', () => {
      selected = index; stage = 0; render();
      $('case-list').querySelector(`[data-case="${entry.id}"]`).focus();
    });
    return button;
  }));
  const head = headline(item);
  $('verdict-text').textContent = head.text;
  $('verdict-mark').dataset.tone = head.tone;
  $('verdict-kicker').textContent = head.kicker;
  for (const tab of $('stages').querySelectorAll('button')) {
    const active = Number(tab.dataset.stage) === stage;
    tab.setAttribute('aria-selected', String(active));
    tab.tabIndex = active ? 0 : -1;
  }
  const panel = $('stage-content');
  panel.replaceChildren();
  panel.setAttribute('aria-labelledby', `stage-tab-${stage}`);
  const heading = element('div', undefined, 'stage-heading');
  heading.append(element('h2', stageTitles(item)[stage]), element('span', stage === 3 ? 'Oracle check' : 'Recorded evidence', 'badge'));
  panel.append(heading);
  const description = [
    'The existing suite passes on this changed implementation. The next stage shows the authored planner reply and the tests produced by the recorded pipeline.',
    'These are the actual authored fixture replies consumed by ScriptedModel. The pipeline runs the generated files together with the existing repository tests.',
    item.kind === 'caught' ? 'The recorded tests expose the changed implementation. A failing assertion is useful evidence: TestPilot keeps it when the authored repair reply identifies a code bug.' : 'The generated suite passes, but the even-length regression remains outside these assertions. Continue to the independent boundary witness before treating this as a fix.',
    item.explanation,
  ][stage];
  panel.append(element('p', description, 'stage-description'));
  const columns = element('div', undefined, 'columns');
  if (stage === 0) {
    columns.append(diffColumn(item, true),
      pendingColumn('Generated tests', 'col-tests', 'Shown in the Tests stage.'),
      pendingColumn('Run and repairs', 'col-run', 'Shown in the Run stage.'));
  } else if (stage === 1) {
    columns.append(diffColumn(item, false), testsColumn(item, true, false),
      pendingColumn('Run and repairs', 'col-run', 'Shown in the Run stage.'));
  } else if (stage === 2) {
    columns.append(diffColumn(item, false), testsColumn(item, false, false), runsColumn(item, 2, true));
  } else {
    columns.append(diffColumn(item, false), testsColumn(item, false, true), runsColumn(item, 3, true));
  }
  panel.append(columns);
  artifact('download-patch', item, 'testpilot.patch');
  artifact('download-record', item, 'record.json');
  artifact('download-log', item, 'generated.log');
  $('previous').disabled = stage === 0;
  $('next').disabled = false;
  $('next').textContent = ['Inspect tests →', 'Read recorded run →', 'Check oracle →', 'Start over ↻'][stage];
  $('step-count').textContent = `Step ${stage + 1} of 4 · ${stageNames[stage]}`;
  $('case-position').textContent = `Fixture ${selected + 1} of ${dataset.cases.length}`;
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
