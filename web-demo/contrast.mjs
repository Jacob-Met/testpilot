// SPDX-License-Identifier: Apache-2.0
// Passive two-fixture evidence contrast. No model, test runner or external dependency.
const $ = (id) => document.getElementById(id);
const names = ['Change', 'Generated tests', 'Execution', 'Independent control'];
let capture;
let state = {left: '', right: '', stage: 0};

function elt(tag, text, klass) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (klass) node.className = klass;
  return node;
}

function validate(data) {
  if (data?.schema !== 'testpilot.offline-replay.v1' ||
      data.execution?.backend !== 'ScriptedModel' || data.execution?.live_model_calls !== 0 ||
      !/^[0-9a-f]{40}$/.test(data.source?.commit) ||
      !Array.isArray(data.cases) || data.cases.length !== 2 ||
      new Set(data.cases.map(c => c.id)).size !== 2) throw new Error('Unsupported capture format.');
  for (const c of data.cases) {
    if (typeof c.id !== 'string' || !/^[a-z0-9_]+$/.test(c.id) ||
        !['caught', 'missed'].includes(c.kind) ||
        !['suspected_code_bug','passed'].includes(c.status) ||
        !['title', 'module', 'function', 'bug', 'diff', 'plan', 'witness', 'oracle', 'message'].every(k => typeof c[k] === 'string') ||
        !c.generated_tests || typeof c.generated_tests !== 'object' ||
        !Object.values(c.generated_tests).every(x => typeof x === 'string'))
      throw new Error('Capture is missing evidence fields.');
    for (const key of ['baseline', 'generated', 'fixed', 'witness_buggy', 'witness_fixed']) {
      const r = c.runs?.[key];
      if (!r || !Number.isInteger(r.passed) || !Number.isInteger(r.failed) ||
          r.errors || r.timed_out || r.skipped || typeof r.output !== 'string' ||
          typeof r.ok !== 'boolean') throw new Error('Recorded test run is incomplete.');
    }
    if (!c.runs.baseline.ok || !c.runs.fixed.ok || c.runs.witness_buggy.ok ||
        !c.runs.witness_fixed.ok ||
        (c.kind === 'caught' && (c.runs.generated.ok || c.status !== 'suspected_code_bug')) ||
        (c.kind === 'missed' && (!c.runs.generated.ok || c.status !== 'passed')))
      throw new Error('Recorded verdict contradicts its test evidence.');
  }
  return data;
}

function restore() {
  const query = new URL(location.href).searchParams;
  const ids = capture.cases.map(c => c.id);
  let left = query.get('left'); let right = query.get('right');
  if (!ids.includes(left)) left = ids[0];
  if (!ids.includes(right) || right === left) right = ids.find(id => id !== left);
  const n = Number(query.get('stage'));
  state = {left, right, stage: Number.isInteger(n) && n >= 1 && n <= 4 ? n - 1 : 0};
}

function writeRoute(mode) {
  if (mode === 'none') return;
  const url = new URL(location.href);
  url.searchParams.set('left', state.left);
  url.searchParams.set('right', state.right);
  url.searchParams.set('stage', String(state.stage + 1));
  history[mode === 'replace' ? 'replaceState' : 'pushState']({}, '', url);
}

function section(title, value, pre = false) {
  const wrap = elt('section', undefined, 'evidence-section');
  wrap.append(elt('h3', title));
  if (pre) {
    const preNode = elt('pre');
    preNode.tabIndex = 0;
    preNode.append(elt('code', value));
    wrap.append(preNode);
  } else wrap.append(elt('p', value));
  return wrap;
}

function outcome(label, run, note) {
  const node = elt('div', undefined, 'outcome-row');
  node.append(elt('span', label), elt('strong', run.passed + ' pass / ' + run.failed + ' fail', run.ok ? 'passed' : 'failed'));
  if (note) node.append(elt('small', note));
  return node;
}
function finding(kind, title, body) {
  const box = elt('aside', undefined, 'key-finding');
  box.append(elt('strong', title), elt('p', body));
  return box;
}
function lane(item, id, ordinal) {
  const box = elt('section', undefined, 'evidence-lane ' + item.kind);
  box.dataset.fixture = item.id;
  box.append(elt('span', ordinal + ' / RECORDED FIXTURE', 'lane-number'));
  const heading = elt('div', undefined, 'lane-heading');
  heading.append(elt('h2', item.title), elt('span', item.kind === 'caught' ? 'CAUGHT' : 'MISSED', 'result-stamp'));
  box.append(heading, elt('p', item.module + ' · ' + item.function + '()', 'lane-meta'),
    elt('p', item.bug, 'lane-claim'), elt('div', undefined, 'lane-keyline'));
  const content = elt('div', undefined, 'lane-content');
  if (state.stage === 0) {
    content.append(section('01 / Exact fixture diff', item.diff, true),
      finding(item.kind, 'WHAT CHANGED', item.kind === 'caught' ?
        'The generated assertions expose this change.' :
        'The generated assertions do not cover the critical boundary.'));
  } else if (state.stage === 1) {
    content.append(section('02 / Recorded authored planner reply', item.plan, true));
    for (const [file, source] of Object.entries(item.generated_tests))
      content.append(section('Generated · ' + file, source, true));
    content.append(finding(item.kind, 'NOT A LIVE GENERATION',
      'These are captured scripted responses. The independently authored control was not provided to ScriptedModel.'));
  } else if (state.stage === 2) {
    content.append(outcome('Existing suite · changed code', item.runs.baseline, 'Recorded baseline'),
      outcome('Generated suite · changed code', item.runs.generated, 'The critical distinction'),
      outcome('Generated suite · oracle fix', item.runs.fixed, 'Same assertions, corrected source'),
      section('03 / Actual saved pytest output', item.runs.generated.output, true),
      finding(item.kind, item.kind === 'caught' ? 'FAILURE IS USEFUL EVIDENCE' : 'A GREEN RESULT IS NOT PROOF', item.message));
  } else {
    content.append(outcome('Generated assertions · changed code', item.runs.generated),
      outcome('Generated assertions · oracle fix', item.runs.fixed),
      outcome('Independent witness · changed code', item.runs.witness_buggy),
      outcome('Independent witness · oracle fix', item.runs.witness_fixed),
      finding(item.kind, item.kind === 'caught' ? 'REGRESSION EXPOSED' : 'BLIND SPOT REVEALED',
        item.kind === 'caught' ?
          'The generated assertions fail on the changed code and pass with the oracle fix.' :
          'The generated assertions pass on the buggy code. A separately authored boundary witness fails there and passes with the oracle fix.'),
      section('04 / Independently authored witness', item.witness, true));
    const details = elt('details', undefined, 'oracle-details');
    details.append(elt('summary', 'Inspect the retained ground-truth source'),
      section('Fixture oracle (never supplied to ScriptedModel)', item.oracle, true));
    content.append(details);
  }
  box.append(content);
  const link = elt('a', 'Open ' + item.title + ' in the verified single replay ↗', 'lane-replay-link');
  link.id = 'open-' + id;
  link.href = './?case=' + encodeURIComponent(item.id) + '&stage=' + (state.stage + 1);
  box.append(link);
  return box;
}

function render(mode = 'push') {
  writeRoute(mode);
  const left = capture.cases.find(c => c.id === state.left);
  const right = capture.cases.find(c => c.id === state.right);
  if (!left || !right || left === right) throw new Error('Invalid comparison selection.');
  $('comparison').replaceChildren(lane(left,'left','A'), lane(right,'right','B'));
  $('comparison').setAttribute('aria-labelledby', 'stage-tab-' + state.stage);
  for (const b of $('stages').querySelectorAll('button')) {
    const active = Number(b.dataset.stage) === state.stage;
    b.setAttribute('aria-selected', String(active));
    b.tabIndex = active ? 0 : -1;
  }
  $('previous').disabled = state.stage === 0;
  $('next').disabled = state.stage === 3;
  $('next').textContent = state.stage === 3 ? 'All evidence inspected' : 'Next: ' + names[state.stage + 1] + ' →';
  $('stage-position').textContent = 'Step ' + (state.stage + 1) + ' of 4 · ' + names[state.stage];
}
function toStage(n) {
  if (!capture || n < 0 || n > 3) return;
  state.stage = n; render();
}
$('stages').addEventListener('click', e => {
  const tab = e.target.closest('button[data-stage]');
  if (tab) toStage(Number(tab.dataset.stage));
});
$('stages').addEventListener('keydown', e => {
  if (!['ArrowRight','ArrowLeft','Home','End'].includes(e.key)) return;
  e.preventDefault();
  const next = e.key === 'Home' ? 0 : e.key === 'End' ? 3 :
    (state.stage + (e.key === 'ArrowRight' ? 1 : 3)) % 4;
  toStage(next); $('stage-tab-' + next).focus();
});
$('swap').addEventListener('click', () => {
  if (!capture) return;
  [state.left,state.right] = [state.right,state.left];
  render();
});
$('previous').addEventListener('click', () => toStage(state.stage - 1));
$('next').addEventListener('click', () => toStage(state.stage + 1));
window.addEventListener('popstate', () => {
  if (!capture) return;
  restore(); render('none');
});
try {
  const response = await fetch('data/replays.json', {cache:'no-store'});
  if (!response.ok) throw new Error('Recording unavailable (HTTP ' + response.status + ').');
  capture = validate(await response.json());
  restore(); render('replace');
  $('capture-source').textContent = 'Source ' + capture.source.commit.slice(0, 12);
} catch (err) {
  $('load-error').textContent = 'Cannot compare this recording: ' + err.message;
  $('load-error').hidden = false;
  $('comparison').replaceChildren();
  $('comparison').append(elt('p', 'Recorded evidence could not be validated.', 'loading'));
}
$('contrast').setAttribute('aria-busy','false');
