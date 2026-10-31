// SPDX-License-Identifier: Apache-2.0
// Native browser acceptance. Uses an installed Playwright/Chromium when supplied.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createServer } from 'node:http';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = path.resolve(process.argv[2] || new URL('..', import.meta.url).pathname);
const output = path.resolve(process.argv[3] || path.join(root, 'receipts/browser'));
const moduleName = process.env.TESTPILOT_PLAYWRIGHT_MODULE || 'playwright';
const { chromium } = await import(path.isAbsolute(moduleName) ? pathToFileURL(moduleName).href : moduleName);
const dataset = JSON.parse(await readFile(path.join(root, 'data/replays.json'), 'utf8'));
await mkdir(path.join(output, 'downloads'), { recursive: true });
const checks = [];
const downloads = [];
const pageErrors = [];
const externalRequests = [];
const mime = { '.html': 'text/html', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.log': 'text/plain', '.py': 'text/plain', '.diff': 'text/plain', '.patch': 'text/plain' };
const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://localhost');
    const rel = decodeURIComponent(url.pathname).replace(/^\/+/, '') || 'index.html';
    const file = path.resolve(root, rel);
    if (!file.startsWith(root + path.sep)) throw new Error('outside receiver');
    const bytes = await readFile(file);
    res.writeHead(200, { 'content-type': mime[path.extname(file)] || 'application/octet-stream', 'cache-control': 'no-store' });
    res.end(bytes);
  } catch { res.writeHead(404); res.end('Not found'); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const options = { headless: true };
if (process.env.TESTPILOT_BROWSER_EXECUTABLE) options.executablePath = process.env.TESTPILOT_BROWSER_EXECUTABLE;
let browser;
let error;

function check(label, value) {
  checks.push({ label, passed: Boolean(value) });
  assert.ok(value, label);
}

try {
  browser = await chromium.launch(options);
  for (const viewport of [{ name: 'desktop', width: 1440, height: 1000 }, { name: 'phone', width: 390, height: 844 }]) {
    const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, acceptDownloads: true, reducedMotion: 'reduce' });
    await context.route('**/*', route => {
      const url = route.request().url();
      if (url.startsWith(origin + '/') || url.startsWith('data:')) return route.continue();
      externalRequests.push(url);
      return route.abort();
    });
    const page = await context.newPage();
    page.on('pageerror', e => pageErrors.push(String(e)));
    await page.goto(origin);
    await page.locator('#replay[aria-busy="false"]').waitFor();
    check(`${viewport.name}: explicit recorded ScriptedModel label`, await page.locator('.disclosure').innerText().then(s => s.includes('ScriptedModel') && s.includes('No live model calls')));
    check(`${viewport.name}: skip link concealed before focus`, await page.locator('.skip-link').evaluate(e => getComputedStyle(e).opacity === '0'));
    await page.keyboard.press('Tab');
    check(`${viewport.name}: keyboard skip link visible`, await page.locator('.skip-link').evaluate(e => document.activeElement === e && getComputedStyle(e).opacity === '1'));
    await page.keyboard.press('Enter');
    check(`${viewport.name}: skip link reaches replay`, await page.evaluate(() => document.activeElement.id) === 'stage-content');
    for (const item of dataset.cases) {
      await page.locator(`[data-case="${item.id}"]`).click();
      check(`${viewport.name}/${item.id}: fixture switch resets stage and retains focus`, await page.locator('#stage-tab-0').getAttribute('aria-selected') === 'true' && await page.evaluate(() => document.activeElement.dataset.case) === item.id);
      await page.locator('#integrity-status[data-state="verified"]').waitFor();
      check(`${viewport.name}/${item.id}: boundary witness is independently labeled`, (await page.locator('#download-witness').innerText()).includes('boundary witness') && (await page.locator('#download-witness').getAttribute('title')).includes('Independently authored control'));
      check(`${viewport.name}/${item.id}: browser SHA-256 verification unlocks checked bytes`,
        (await page.locator('#integrity-status').innerText()).includes('4/4') &&
        await page.locator('#download-patch').getAttribute('data-sha256') === item.files['testpilot.patch'].sha256 &&
        (await page.locator('#download-patch').getAttribute('href')).startsWith('blob:'));
      for (let i = 0; i < 4; i++) {
        check(`${viewport.name}/${item.id}: stage ${i + 1} selected`, await page.locator(`#stage-tab-${i}`).getAttribute('aria-selected') === 'true');
        check(`${viewport.name}/${item.id}: stage ${i + 1} fits viewport`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        if (i === 2) {
          const rendered = await page.locator('#stage-content').innerText();
          check(`${viewport.name}/${item.id}: actual generated run outcome`, rendered.includes(item.runs.generated.output.trim()) && rendered.includes(item.kind === 'caught' ? 'Code bug suspected' : 'boundary still untested'));
        }
        if (i < 3) await page.locator('#next').click();
      }
      const rendered = await page.locator('#stage-content').innerText();
      check(`${viewport.name}/${item.id}: oracle and independent witness visible`, rendered.includes('Boundary witness') && rendered.includes(item.witness.trim()));
      for (const [id, filename] of [['download-patch', 'testpilot.patch'], ['download-record', 'record.json'], ['download-log', 'generated.log'], ['download-witness', 'witness.py']]) {
        const [download] = await Promise.all([page.waitForEvent('download'), page.locator(`#${id}`).click()]);
        const dest = path.join(output, 'downloads', `${viewport.name}-${item.id}-${filename}`);
        await download.saveAs(dest);
        const bytes = await readFile(dest);
        const sha256 = createHash('sha256').update(bytes).digest('hex');
        check(`${viewport.name}/${item.id}: exact ${filename} download`, sha256 === item.files[filename].sha256 && bytes.length === item.files[filename].bytes);
        downloads.push({ viewport: viewport.name, case: item.id, filename, bytes: bytes.length, sha256 });
      }
      if (item.id === 'stats_median' && viewport.name === 'phone') await page.screenshot({ path: path.join(output, 'phone.png'), fullPage: true });
    }
    await page.locator('#stage-tab-0').click();
    await page.locator('#stage-tab-0').focus();
    await page.keyboard.press('ArrowRight');
    check(`${viewport.name}: keyboard stage navigation`, await page.evaluate(() => document.activeElement.id) === 'stage-tab-1' && await page.locator('#stage-tab-1').getAttribute('aria-selected') === 'true');
    await page.keyboard.press('End');
    check(`${viewport.name}: keyboard End`, await page.locator('#stage-tab-3').getAttribute('aria-selected') === 'true');
    await page.keyboard.press('Home');
    check(`${viewport.name}: keyboard Home`, await page.locator('#stage-tab-0').getAttribute('aria-selected') === 'true');
    // A replay is navigable history, not just a final URL. Test actual Back/Forward.
    await page.goto(`${origin}/?case=calc_clamp&stage=1&ref=browser-check`);
    await page.locator('#replay[aria-busy="false"]').waitFor();
    await page.locator('#next').click();
    await page.locator('#next').click();
    await page.goBack();
    await page.locator('#stage-tab-1[aria-selected="true"]').waitFor();
    check(`${viewport.name}: Back restores prior replay stage`, await page.locator('#stage-tab-1').getAttribute('aria-selected') === 'true');
    check(`${viewport.name}: history preserves unrelated query parameters`, new URL(page.url()).searchParams.get('ref') === 'browser-check');
    await page.goForward();
    await page.locator('#stage-tab-2[aria-selected="true"]').waitFor();
    check(`${viewport.name}: Forward restores replay stage`, await page.locator('#stage-tab-2').getAttribute('aria-selected') === 'true');
    await page.locator('[data-case="stats_median"]').click();
    await page.goBack();
    await page.locator('[data-case="calc_clamp"][aria-pressed="true"]').waitFor();
    check(`${viewport.name}: Back restores fixture and stage`, await page.locator('#stage-tab-2').getAttribute('aria-selected') === 'true');
    await page.goForward();
    await page.locator('[data-case="stats_median"][aria-pressed="true"]').waitFor();
    check(`${viewport.name}: Forward restores fixture and its first stage`, await page.locator('#stage-tab-0').getAttribute('aria-selected') === 'true');
    await page.goto(`${origin}/?case=stats_median&stage=4`);
    await page.locator('#replay[aria-busy="false"]').waitFor();
    check(`${viewport.name}: exact fixture/stage deep link`, await page.locator('[data-case="stats_median"]').getAttribute('aria-pressed') === 'true' && await page.locator('#stage-tab-3').getAttribute('aria-selected') === 'true');
    await page.goto(`${origin}/?case=missing&stage=99`);
    await page.locator('#replay[aria-busy="false"]').waitFor();
    check(`${viewport.name}: unknown deep link has deterministic fallback`, await page.locator('[data-case="calc_clamp"]').getAttribute('aria-pressed') === 'true' && await page.locator('#stage-tab-0').getAttribute('aria-selected') === 'true');
    if (viewport.name === 'desktop') await page.screenshot({ path: path.join(output, 'desktop.png'), fullPage: true });
    await context.close();
  }
  const tampered = await browser.newContext();
  await tampered.route('**/data/cases/calc_clamp/testpilot.patch', route =>
    route.fulfill({ status: 200, body: 'tampered evidence', contentType: 'application/octet-stream' }));
  const damaged = await tampered.newPage();
  await damaged.goto(origin);
  await damaged.locator('#integrity-status[data-state="failed"]').waitFor();
  check('altered downloaded bytes are refused', (await damaged.locator('#integrity-status').innerText()).includes('mismatch') &&
    await damaged.locator('#download-patch').getAttribute('href') === null &&
    await damaged.locator('#download-record').getAttribute('href') === null &&
    await damaged.locator('#download-witness').getAttribute('href') === null);
  await tampered.close();

  const missing = await browser.newContext();
  await missing.route('**/data/cases/calc_clamp/generated.log', route => route.fulfill({ status: 404, body: 'gone' }));
  const incomplete = await missing.newPage();
  await incomplete.goto(origin);
  await incomplete.locator('#integrity-status[data-state="failed"]').waitFor();
  check('missing artifact keeps all downloads locked', (await incomplete.locator('#integrity-status').innerText()).includes('HTTP 404') &&
    await incomplete.locator('#download-log').getAttribute('href') === null);
  await missing.close();

  for (const broken of [
    { label: 'same-size witness corruption', status: 200, body: 'x'.repeat(dataset.cases[0].files['witness.py'].bytes), error: 'SHA-256 mismatch' },
    { label: 'unavailable witness', status: 404, body: 'gone', error: 'HTTP 404' },
  ]) {
    const ctx = await browser.newContext();
    await ctx.route('**/data/cases/calc_clamp/witness.py', route =>
      route.fulfill({ status: broken.status, body: broken.body, contentType: 'text/plain' }));
    const page = await ctx.newPage();
    await page.goto(origin);
    await page.locator('#integrity-status[data-state="failed"]').waitFor();
    const hrefs = await Promise.all(['download-patch', 'download-record', 'download-log', 'download-witness'].map(id =>
      page.locator(`#${id}`).getAttribute('href')));
    check(`${broken.label} locks all four recorded downloads`,
      (await page.locator('#integrity-status').innerText()).includes(broken.error) && hrefs.every(h => h === null));
    await ctx.close();
  }

  const stale = await browser.newContext();
  await stale.route('**/data/cases/calc_clamp/testpilot.patch', async route => {
    await new Promise(resolve => setTimeout(resolve, 350));
    await route.continue();
  });
  const switched = await stale.newPage();
  await switched.goto(origin);
  await switched.locator('#replay[aria-busy="false"]').waitFor();
  await switched.locator('[data-case="stats_median"]').click();
  await switched.locator('#integrity-status[data-state="verified"]').waitFor();
  await switched.waitForTimeout(450);
  check('late prior-fixture verification cannot unlock a different fixture',
    await switched.locator('#download-patch').getAttribute('download') === 'stats_median-testpilot.patch' &&
    await switched.locator('#download-patch').getAttribute('data-sha256') === dataset.cases[1].files['testpilot.patch'].sha256 &&
    await switched.locator('#download-witness').getAttribute('data-sha256') === dataset.cases[1].files['witness.py'].sha256);
  await stale.close();

  const negative = await browser.newContext();
  await negative.route('**/data/replays.json', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...dataset, execution: { ...dataset.execution, live_model_calls: 1 } }) }));
  const bad = await negative.newPage();
  await bad.goto(origin);
  await bad.locator('#load-error:not([hidden])').waitFor();
  check('invalid evidence fails closed', await bad.locator('#replay').isHidden() && (await bad.locator('#load-error').innerText()).includes('unsupported format'));
  await negative.close();
  check('no external browser requests', externalRequests.length === 0);
  check('no browser page errors', pageErrors.length === 0);
} catch (e) { error = String(e.stack || e); }
finally {
  const receipt = { node: process.version, browser: browser?.version(), source_commit: dataset.source.commit,
    root, checks, downloads, externalRequests, pageErrors, error: error || null };
  await writeFile(path.join(output, 'receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
  console.log(JSON.stringify({ passed: checks.filter(c => c.passed).length, failed: checks.filter(c => !c.passed).length, downloads: downloads.length, output, error: error || null }));
}
if (error) process.exitCode = 1;
