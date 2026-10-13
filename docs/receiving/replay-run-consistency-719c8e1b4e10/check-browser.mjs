// SPDX-License-Identifier: Apache-2.0
// Focused native-browser check for recorded-run evidence admission.
(async function main() {
  const assert = (await import('node:assert/strict')).default;
  const { createHash } = await import('node:crypto');
  const { readFile, writeFile, mkdir, mkdtemp, rm } = await import('node:fs/promises');
  const { createServer } = await import('node:http');
  const { spawn } = await import('node:child_process');
  const path = await import('node:path');
  const { fileURLToPath } = await import('node:url');
  const args = {};
  for (let i = 2; i < process.argv.length; i += 2) {
    const key = process.argv[i];
    assert.ok(['--browser', '--root', '--original-app', '--output'].includes(key) && process.argv[i + 1], 'Use --browser PATH --root WEB_DEMO --original-app ORIGINAL_APP --output NEW_DIRECTORY');
    assert.ok(!Object.hasOwn(args, key), 'Do not repeat arguments.');
    args[key] = process.argv[i + 1];
  }
  for (const key of ['--browser', '--root', '--original-app', '--output']) assert.ok(args[key], key + ' is required.');
  const root = path.resolve(args['--root']), output = path.resolve(args['--output']);
  const digest = data => createHash('sha256').update(data).digest('hex');
  const sources = new Map();
  for (const name of ['index.html', 'styles.css', 'app.mjs', 'data/replays.json']) sources.set(name, await readFile(path.join(root, name)));
  const originalPath = path.resolve(args['--original-app']), originalApp = await readFile(originalPath);
  const dataset = JSON.parse(sources.get('data/replays.json').toString('utf8'));
  const variants = {
    healthy: data => data,
    'contradictory-exit': data => { data.cases[0].runs.baseline.returncode = 1; return data; },
    'absent-cases': data => { delete data.cases[0].runs.generated.cases; return data; },
    'inconsistent-failure-count': data => { data.cases[1].runs.witness_buggy.failed = 0; return data; },
    'missing-timeout-result': data => { delete data.cases[1].runs.fixed.timed_out; return data; },
  };
  const cases = new Map(Object.entries(variants).map(([name, edit]) => [name, Buffer.from(JSON.stringify(edit(structuredClone(dataset))))]));
  await mkdir(output);
  const owned = await mkdtemp(path.join(output, 'browser-')), profile = path.join(owned, 'profile');
  await mkdir(profile);
  const receipt = {
    schema: 'testpilot.run_evidence.browser.v1', startedAt: new Date().toISOString(),
    node: process.version, root, originalApp: originalPath, scope: 'Native rendered healthy views and evidence refusal; no physical-download or independent-review claim.',
    sourcePins: [...sources].map(([name, bytes]) => ({path: name, bytes: bytes.length, sha256: digest(bytes)})),
    originalAppSha256: digest(originalApp), checks: [], externalPageRequests: [], pageErrors: [], screenshots: [],
  };
  const servedDatasets = [];
  receipt.servedDatasets = servedDatasets;
  const server = createServer((req, res) => {
    const parts = new URL(req.url, 'http://127.0.0.1').pathname.split('/').filter(Boolean);
    const [side, scenario, ...rest] = parts, name = rest.join('/');
    if (!['original', 'candidate'].includes(side) || !cases.has(scenario)) { res.writeHead(404).end(); return; }
    const bytes = name === 'data/replays.json' ? cases.get(scenario) : name === 'app.mjs' && side === 'original' ? originalApp : sources.get(name);
    if (!bytes) { res.writeHead(404).end(); return; }
    if (name === 'data/replays.json') servedDatasets.push({side, scenario, sha256:digest(bytes)});
    const mime = name.endsWith('.html') ? 'text/html' : name.endsWith('.css') ? 'text/css' : name.endsWith('.json') ? 'application/json' : 'text/javascript';
    res.writeHead(200, {'Content-Type': mime + ';charset=utf-8', 'Cache-Control': 'no-store'}).end(bytes);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  let browser, socket, sessionId, nextId = 0, browserLog = '', launchError;
  const pending = new Map();
  function command(method, params = {}, scoped = true) {
    const id = ++nextId;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { pending.delete(id); reject(new Error('CDP timeout ' + method)); }, 12000);
      pending.set(id, {resolve, reject, timer});
      socket.send(JSON.stringify({id, method, params, ...(scoped && sessionId ? {sessionId} : {})}));
    });
  }
  async function evaluate(expression) {
    const r = await command('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result.value;
  }
  async function waitFor(fn, label, count = 120) {
    let last;
    for (let i = 0; i < count; i++) {
      try { const value = await fn(); if (value) return value; } catch (error) { last = error; }
      await sleep(100);
    }
    throw new Error('Timed out: ' + label + (last ? '; ' + last.message : ''));
  }
  async function snapshot() {
    return evaluate(`(() => {
      const replay = document.querySelector('#replay'), error = document.querySelector('#load-error');
      return {
        url: location.href, documentComplete: document.readyState === 'complete',
        ready: replay.getAttribute('aria-busy') === 'false', replayHidden: replay.hidden,
        errorHidden: error.hidden, errorText: error.textContent,
        case: document.querySelector('[data-case][aria-pressed="true"]')?.dataset.case ?? null,
        stage: document.querySelector('[data-stage][aria-selected="true"]')?.dataset.stage ?? null,
        rendered: document.querySelector('#stage-content').innerText,
        links: ['download-patch','download-record','download-log'].map(id => { const e=document.getElementById(id); return {id,href:e.getAttribute('href'),disabled:e.getAttribute('aria-disabled')}; }),
        fits: document.documentElement.scrollWidth <= innerWidth,
        sourceHref: document.querySelector('#source-link').getAttribute('href')
      };
    })()`);
  }
  async function open(side, variant, item, stage) {
    const url = `${origin}/${side}/${variant}/index.html?case=${item}&stage=${stage}`;
    await command('Page.navigate', {url});
    await waitFor(async () => {
      const value = await snapshot();
      return value.url === url && value.documentComplete && (value.ready || !value.errorHidden);
    }, 'replay admission or refusal');
    return snapshot();
  }
  function check(label, action, details) {
    action();
    receipt.checks.push({label, passed: true, ...(details ? {details} : {})});
  }
  try {
    browser = spawn(args['--browser'], ['--headless=new', '--disable-gpu', '--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-first-run', '--no-default-browser-check', '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0', '--user-data-dir=' + profile, 'about:blank'], {stdio: ['ignore', 'ignore', 'pipe']});
    browser.stderr.on('data', chunk => { browserLog = (browserLog + chunk.toString()).slice(-8000); });
    browser.on('error', error => { launchError = error; });
    const port = await waitFor(async () => {
      if (launchError) throw launchError;
      if (browser.exitCode !== null) throw new Error('Browser exited ' + browser.exitCode);
      return (await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).trim().split('\n');
    }, 'browser launch', 300);
    socket = new WebSocket(`ws://127.0.0.1:${port[0]}${port[1]}`);
    socket.addEventListener('message', event => {
      const message = JSON.parse(event.data);
      if (message.id) {
        const p = pending.get(message.id);
        if (!p) return;
        clearTimeout(p.timer); pending.delete(message.id);
        message.error ? p.reject(new Error(message.error.message)) : p.resolve(message.result);
      } else if (message.method === 'Runtime.exceptionThrown') receipt.pageErrors.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
      else if (message.method === 'Network.requestWillBeSent') {
        const url = message.params.request.url;
        if (/^https?:/.test(url) && !url.startsWith(origin + '/')) receipt.externalPageRequests.push(url);
      }
    });
    await new Promise((resolve, reject) => {
      socket.addEventListener('open', resolve, {once: true});
      socket.addEventListener('error', reject, {once: true});
    });
    receipt.browser = await command('Browser.getVersion', {}, false);
    const {targetId} = await command('Target.createTarget', {url: 'about:blank'}, false);
    ({sessionId} = await command('Target.attachToTarget', {targetId, flatten: true}, false));
    for (const method of ['Page.enable', 'Runtime.enable', 'Network.enable']) await command(method);
    await command('Emulation.setDeviceMetricsOverride', {width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false});
    const original = await open('original', 'contradictory-exit', 'calc_clamp', 4);
    check('original app renders a contradictory successful run and enables artifact links', () => {
      assert.equal(original.ready, true); assert.equal(original.replayHidden, false);
      assert.equal(original.errorHidden, true); assert.equal(original.stage, '3');
      assert.ok(original.links.every(link => link.href && link.disabled !== 'true'));
    }, original);
    for (const viewport of [{name: 'desktop', width: 1440, height: 1000}, {name: 'phone', width: 390, height: 844}]) {
      await command('Emulation.setDeviceMetricsOverride', {width: viewport.width, height: viewport.height, deviceScaleFactor: 1, mobile: viewport.name === 'phone'});
      for (const item of dataset.cases) for (let stage = 1; stage <= 4; stage++) {
        const view = await open('candidate', 'healthy', item.id, stage);
        check(`${viewport.name}/${item.id}/stage-${stage}: healthy rendered replay and exact evidence links`, () => {
          assert.equal(view.ready, true); assert.equal(view.replayHidden, false); assert.equal(view.errorHidden, true);
          assert.equal(view.case, item.id); assert.equal(view.stage, String(stage - 1)); assert.equal(view.fits, true);
          assert.equal(view.sourceHref, `https://github.com/Jacob-Met/testpilot/commit/${dataset.source.commit}`);
          const expected = ['testpilot.patch', 'record.json', 'generated.log'].map(name => item.files[name].url);
          assert.deepEqual(view.links.map(link => link.href), expected);
          assert.ok(view.links.every(link => link.disabled !== 'true'));
          if (stage === 3) assert.ok(view.rendered.includes(item.runs.generated.output.trim()));
          if (stage === 4) assert.ok(view.rendered.includes(item.witness.trim()));
        }, {case:item.id, stage, viewport:viewport.name});
      }
      const {data} = await command('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true});
      const bytes = Buffer.from(data, 'base64'), name = viewport.name + '.png';
      await writeFile(path.join(output, name), bytes);
      receipt.screenshots.push({path:name,bytes:bytes.length,sha256:digest(bytes)});
    }
    for (const scenario of Object.keys(variants).filter(name => name !== 'healthy')) {
      const view = await open('candidate', scenario, 'calc_clamp', 4);
      check(`${scenario}: native browser refuses evidence before rendering or enabling downloads`, () => {
        assert.equal(view.replayHidden, true); assert.equal(view.errorHidden, false);
        const expected = ['absent-cases', 'missing-timeout-result'].includes(scenario)
          ? 'A required fixture run is incomplete.' : 'A required fixture run has inconsistent results.';
        assert.ok(view.errorText.includes(expected));
        assert.equal(view.ready, false);
        assert.ok(view.links.every(link => link.href === null && link.disabled === 'true'));
        assert.match(view.rendered, /Loading recorded evidence/);
      }, {scenario, errorText:view.errorText});
    }
    assert.equal(servedDatasets.length, 21);
    assert.equal(servedDatasets.filter(x => x.side === 'candidate' && x.scenario === 'healthy').length, 16);
    for (const scenario of Object.keys(variants).filter(name => name !== 'healthy'))
      assert.equal(servedDatasets.filter(x => x.side === 'candidate' && x.scenario === scenario).length, 1);
    assert.deepEqual(receipt.pageErrors, []);
    assert.deepEqual(receipt.externalPageRequests, []);
    receipt.status = 'passed';
  } catch (error) {
    receipt.status = 'failed'; receipt.error = error.stack; receipt.browserLog = browserLog;
  } finally {
    for (const [name, bytes] of sources) {
      if (!(await readFile(path.join(root, name))).equals(bytes)) { receipt.status = 'failed'; receipt.sourceChanged = name; }
    }
    receipt.originalAppUnchanged = (await readFile(originalPath)).equals(originalApp);
    receipt.sourceUnchanged = !receipt.sourceChanged && receipt.originalAppUnchanged;
    if (!receipt.sourceUnchanged) receipt.status = 'failed';
    if (socket?.readyState === WebSocket.OPEN) try { await command('Browser.close', {}, false); } catch {}
    socket?.close();
    for (const p of pending.values()) clearTimeout(p.timer);
    if (browser && browser.exitCode === null && browser.signalCode === null) browser.kill('SIGTERM');
    for (let i = 0; browser && browser.exitCode === null && browser.signalCode === null && i < 30; i++) await sleep(100);
    receipt.browserExited = !browser || browser.exitCode !== null || browser.signalCode !== null;
    if (receipt.browserExited) await rm(owned, {recursive: true, force: true});
    else { receipt.status = 'failed'; receipt.cleanupError = 'Owned browser remains; profile retained.'; }
    server.closeAllConnections(); await new Promise(resolve => server.close(resolve));
    receipt.finishedAt = new Date().toISOString();
    receipt.receiverSha256 = digest(await readFile(fileURLToPath(import.meta.url)));
    await writeFile(path.join(output, 'receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
    console.log(JSON.stringify({status:receipt.status,checks:receipt.checks.length,screenshots:receipt.screenshots,sourceUnchanged:receipt.sourceUnchanged,browserExited:receipt.browserExited,error:receipt.error??null}));
  }
  if (receipt.status !== 'passed') process.exitCode = 1;
})().catch(error => { console.error(error); process.exitCode = 1; });
