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
      for (const [id, filename] of [['download-patch', 'testpilot.patch'], ['download-record', 'record.json'], ['download-log', 'generated.log']]) {
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
    await page.goto(`${origin}/?case=stats_median&stage=4`);
    await page.locator('#replay[aria-busy="false"]').waitFor();
    check(`${viewport.name}: exact fixture/stage deep link`, await page.locator('[data-case="stats_median"]').getAttribute('aria-pressed') === 'true' && await page.locator('#stage-tab-3').getAttribute('aria-selected') === 'true');
    await page.goto(`${origin}/?case=missing&stage=99`);
    await page.locator('#replay[aria-busy="false"]').waitFor();
    check(`${viewport.name}: unknown deep link has deterministic fallback`, await page.locator('[data-case="calc_clamp"]').getAttribute('aria-pressed') === 'true' && await page.locator('#stage-tab-0').getAttribute('aria-selected') === 'true');
    if (viewport.name === 'desktop') await page.screenshot({ path: path.join(output, 'desktop.png'), fullPage: true });
    await context.close();
  }
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
