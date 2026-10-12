// SPDX-License-Identifier: Apache-2.0
// Run the exact browser application with a small DOM and a local fixture response.
// This checks evidence admission and rendering effects; it is not a browser test.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const app = await readFile(new URL('../app.mjs', import.meta.url), 'utf8');
const dataset = JSON.parse(await readFile(new URL('../data/replays.json', import.meta.url), 'utf8'));

function makeReplayDocument() {
  const ids = new Map();
  const document = {
    activeElement: null,
    getElementById(id) {
      if (!ids.has(id)) throw new Error('Unexpected element: ' + id);
      return ids.get(id);
    },
    createElement(tag) { return new Element(tag); },
  };
  class Element {
    constructor(tag = 'div') {
      this.tagName = tag.toUpperCase();
      this.attributes = new Map();
      this.dataset = {};
      this.children = [];
      this.events = new Map();
      this.hidden = false;
      this.disabled = false;
      this._text = '';
    }
    get textContent() { return this._text + this.children.map(child => child.textContent ?? String(child)).join(''); }
    set textContent(value) { this._text = String(value); this.children = []; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this._text = ''; this.children = [...children]; }
    setAttribute(name, value) { this.attributes.set(name, String(value)); }
    getAttribute(name) { return this.attributes.get(name) ?? null; }
    removeAttribute(name) { this.attributes.delete(name); }
    addEventListener(name, callback) { this.events.set(name, callback); }
    querySelectorAll(selector) {
      if (selector !== 'button') throw new Error('Unexpected selector: ' + selector);
      return this.children.filter(child => child.tagName === 'BUTTON');
    }
    querySelector(selector) {
      const match = selector.match(/^\[data-case="([^"]+)"\]$/);
      if (!match) throw new Error('Unexpected selector: ' + selector);
      return this.children.find(child => child.dataset.case === match[1]);
    }
    focus() { document.activeElement = this; }
  }
  for (const id of [
    'case-list', 'stages', 'stage-content', 'download-patch', 'download-record',
    'download-log', 'previous', 'next', 'step-count', 'case-position',
    'announcement', 'source-link', 'runtime', 'recorded-at', 'replay', 'load-error',
  ]) {
    const node = new Element();
    node.id = id;
    ids.set(id, node);
  }
  for (let stage = 0; stage < 4; stage++) {
    const node = new Element('button');
    node.id = 'stage-tab-' + stage;
    node.dataset.stage = String(stage);
    ids.set(node.id, node);
    ids.get('stages').append(node);
  }
  ids.get('load-error').hidden = true;
  ids.get('replay').setAttribute('aria-busy', 'true');
  for (const id of ['download-patch', 'download-record', 'download-log']) {
    ids.get(id).setAttribute('aria-disabled', 'true');
  }
  return document;
}

async function openReplay(source, data, query = '') {
  const document = makeReplayDocument();
  const requests = [];
  const location = { href: 'http://127.0.0.1:8000/' + query };
  const history = { replaceState(_state, _title, url) { location.href = String(url); } };
  const fetch = async url => {
    requests.push(url);
    return { ok: true, status: 200, json: async () => JSON.parse(JSON.stringify(data)) };
  };
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
  await new AsyncFunction('document', 'fetch', 'location', 'history', source)(document, fetch, location, history);
  return { document, requests, location };
}

const mutations = [
  ["count mismatch", r=>{r.passed+=1;}],
  ["negative count", r=>{r.passed=-1;}],
  ["unsafe count", r=>{r.passed=9007199254740992;}],
  ["wrong process exit", r=>{r.returncode=r.ok?1:0;}],
  ["unknown process exit", r=>{r.returncode=null;}],
  ["missing process exit", r=>{delete r.returncode;}],
  ["opposite verdict", r=>{r.ok=!r.ok;}],
  ["string verdict", r=>{r.ok=String(r.ok);}],
  ["missing verdict", r=>{delete r.ok;}],
  ["missing timeout evidence", r=>{delete r.timed_out;}],
  ["missing error count", r=>{delete r.errors;}],
  ["missing skip count", r=>{delete r.skipped;}],
  ["missing cases", r=>{delete r.cases;}],
  ["empty cases", r=>{r.cases=[];}],
  ["unknown case outcome", r=>{r.cases[0].outcome="unavailable";}],
  ["null case", r=>{r.cases[0]=null;}]
];

test('both bundled recordings retain every deep-linked stage and exact download paths', async () => {
  const before = JSON.stringify(dataset);
  for (const item of dataset.cases) {
    for (let stage = 1; stage <= 4; stage++) {
      const result = await openReplay(app, dataset, '?case=' + item.id + '&stage=' + stage);
      const get = id => result.document.getElementById(id);
      const label = item.id + '/stage-' + stage;
      assert.equal(get('replay').hidden, false, label);
      assert.equal(get('replay').getAttribute('aria-busy'), 'false', label);
      assert.equal(get('load-error').hidden, true, label);
      assert.equal(get('stage-tab-' + (stage - 1)).getAttribute('aria-selected'), 'true', label);
      assert.equal(get('case-position').textContent, item.id, label);
      for (const [id, filename] of [
        ['download-patch', 'testpilot.patch'], ['download-record', 'record.json'],
        ['download-log', 'generated.log'],
      ]) {
        assert.equal(get(id).href, item.files[filename].url, label + '/' + filename);
        assert.equal(get(id).dataset.sha256, item.files[filename].sha256, label + '/' + filename);
        assert.equal(get(id).getAttribute('aria-disabled'), null, label + '/' + filename);
      }
      assert.deepEqual(result.requests, ['data/replays.json'], label);
    }
  }
  assert.equal(JSON.stringify(dataset), before);
});

test('inconsistent or incomplete required runs never expose a verdict or download', async () => {
  for (let index = 0; index < dataset.cases.length; index++) {
    for (const name of Object.keys(dataset.cases[index].runs)) {
      for (const [description, mutate] of mutations) {
        const data = JSON.parse(JSON.stringify(dataset));
        mutate(data.cases[index].runs[name]);
        const label = data.cases[index].id + '/' + name + '/' + description;
        const result = await openReplay(app, data);
        const get = id => result.document.getElementById(id);
        assert.equal(get('replay').hidden, true, label);
        assert.equal(get('load-error').hidden, false, label);
        assert.match(get('load-error').textContent, /A required fixture run/, label);
        assert.equal(get('stage-content').textContent, '', label);
        assert.equal(get('case-list').children.length, 0, label);
        for (const id of ['download-patch', 'download-record', 'download-log']) {
          assert.equal(get(id).getAttribute('aria-disabled'), 'true', label);
          assert.equal(get(id).href, undefined, label);
        }
        assert.deepEqual(result.requests, ['data/replays.json'], label);
        assert.equal(result.location.href, 'http://127.0.0.1:8000/', label);
      }
    }
  }
});

test('a complete failing run can contain no passing cases', async () => {
  const data = JSON.parse(JSON.stringify(dataset));
  const run = data.cases[0].runs.generated;
  run.cases = run.cases.map(item => ({ ...item, outcome: 'failed' }));
  run.passed = 0;
  run.failed = run.cases.length;
  const result = await openReplay(app, data, '?case=calc_clamp&stage=3');
  assert.equal(result.document.getElementById('replay').hidden, false);
  assert.match(result.document.getElementById('stage-content').textContent, /Code bug suspected/);
});

test('a failed process without a recorded failing case is not a regression witness', async () => {
  const data = JSON.parse(JSON.stringify(dataset));
  const run = data.cases[0].runs.generated;
  run.cases = run.cases.map(item => ({ ...item, outcome: 'passed' }));
  run.passed = run.cases.length;
  run.failed = 0;
  const result = await openReplay(app, data);
  assert.equal(result.document.getElementById('replay').hidden, true);
  assert.match(result.document.getElementById('load-error').textContent, /inconsistent results/);
});
