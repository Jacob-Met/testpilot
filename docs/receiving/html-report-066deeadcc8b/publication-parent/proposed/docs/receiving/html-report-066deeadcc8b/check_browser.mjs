import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';

const [captureRoot, outputRoot] = process.argv.slice(2);
if (!captureRoot || !outputRoot) throw new Error('usage: node check_browser.mjs CLI_CAPTURE_DIRECTORY NEW_OUTPUT_DIRECTORY');
const modulePath = process.env.TESTPILOT_PLAYWRIGHT_MODULE;
const { chromium } = await import(modulePath ? pathToFileURL(modulePath).href : 'playwright');
const executablePath = process.env.TESTPILOT_BROWSER_EXECUTABLE;
await fs.mkdir(outputRoot, { recursive: false });
const isolated = path.join(outputRoot, 'isolated-pages');
await fs.mkdir(isolated);
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const rawCapture = await fs.readFile(path.join(captureRoot, 'report.json'));
const capture = JSON.parse(rawCapture);
const report = {
  schema: 'testpilot.html_report.author_browser.v1', captureReportSha256: digest(rawCapture),
  driverSha256: digest(await fs.readFile(new URL(import.meta.url))),
  checks: [], cases: [], requests: [], applicationErrors: [], consoleErrors: [],
};
function check(label, actual, expected) {
  const passed = JSON.stringify(actual) === JSON.stringify(expected);
  report.checks.push({ label, actual, expected, passed });
  if (!passed) throw new Error(`${label}: ${JSON.stringify(actual)} != ${JSON.stringify(expected)}`);
}
const browser = await chromium.launch({ executablePath, headless: true });
report.browserVersion = browser.version();
let context;
try {
  context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1200, height: 850 } });
  await context.route('**/*', async route => {
    if (/^https?:/.test(route.request().url())) {
      report.requests.push(route.request().url());
      await route.abort('blockedbyclient');
    } else await route.continue();
  });
  const page = await context.newPage();
  page.on('pageerror', error => report.applicationErrors.push(String(error)));
  page.on('console', message => { if (message.type() === 'error') report.consoleErrors.push(message.text()); });
  for (const item of capture.cases) {
    const root = path.join(captureRoot, item.name, 'out');
    const html = await fs.readFile(path.join(root, 'report.html'));
    const json = await fs.readFile(path.join(root, 'report.json'));
    const patch = await fs.readFile(path.join(root, 'testpilot.patch'));
    const data = JSON.parse(json);
    const standalone = path.join(isolated, `${item.name}.html`);
    await fs.writeFile(standalone, html);
    await page.goto(pathToFileURL(standalone).href, { waitUntil: 'load' });
    check(`${item.name}: source bytes`, digest(await fs.readFile(standalone)), digest(html));
    check(`${item.name}: status`, await page.locator('.status').textContent(), data.status);
    check(`${item.name}: no executable or external elements`, await page.locator('script,iframe,object,embed,img,link,form').count(), 0);
    check(`${item.name}: final generated files`, await page.locator('#tests > details > summary code').allTextContents(), Object.keys(data.test_files).sort());
    const bodies = await page.locator('#tests > details > .detail-body pre code').allTextContents();
    check(`${item.name}: exact final generated source`, bodies, Object.keys(data.test_files).sort().map(key => data.test_files[key]));
    const generated = data.final?.generated;
    const metric = data.final?.junit_available && generated ? `${generated.passed} / ${generated.collected}` : 'Unavailable';
    check(`${item.name}: qualified generated counts`, await page.locator('.metric').first().locator('dd').textContent(), metric);
    check(`${item.name}: repair round records`, await page.locator('#rounds > ol > li').count(), data.rounds.length);
    check(`${item.name}: no document overflow`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    if (data.final) {
      check(`${item.name}: exact recorded case identities`, await page.locator('#result .cases > li > details > summary > code').allTextContents(), data.final.cases.map(c => c.nodeid));
      check(`${item.name}: timeout field`, (await page.locator('#result').innerText()).includes(`Timeout: ${data.final.timed_out ? 'yes' : 'no'}`), true);
    } else {
      check(`${item.name}: no fabricated run`, (await page.locator('#result').innerText()).includes('No generated-test result was recorded.'), true);
    }
    const downloaded = {};
    for (const [name, expected] of [['testpilot.patch', patch], ['report.json', json]]) {
      const pending = page.waitForEvent('download');
      await page.locator(`a[download="${name}"]`).click();
      const download = await pending;
      check(`${item.name}: download filename ${name}`, download.suggestedFilename(), name);
      const destination = path.join(outputRoot, `${item.name}-${name}`);
      await download.saveAs(destination);
      const actual = await fs.readFile(destination);
      check(`${item.name}: exact download ${name}`, digest(actual), digest(expected));
      downloaded[name] = { bytes: actual.length, sha256: digest(actual) };
    }
    report.cases.push({ name: item.name, html: { bytes: html.length, sha256: digest(html) }, downloaded });
    if (item.name === 'repair') {
      await page.getByRole('link', { name: 'Generated files', exact: true }).focus();
      await page.keyboard.press('Enter');
      check('keyboard section navigation', new URL(page.url()).hash, '#tests');
      const summary = page.locator('#tests > details > summary').first();
      await summary.focus();
      await page.keyboard.press('Enter');
      check('keyboard disclosure expands source', await page.locator('#tests > details').first().getAttribute('open'), '');
      await page.keyboard.press('Enter');
      check('keyboard disclosure closes source', await page.locator('#tests > details').first().getAttribute('open'), null);
      await page.goto(pathToFileURL(standalone).href);
      await page.screenshot({ path: path.join(outputRoot, 'desktop-repair.png'), fullPage: true });
      await page.emulateMedia({ media: 'print' });
      check('print reveals closed generated source', await page.locator('#tests > details pre').first().isVisible(), true);
      await page.pdf({ path: path.join(outputRoot, 'repair-print.pdf'), format: 'A4', printBackground: true });
      await page.emulateMedia({ media: 'screen' });
      await page.setViewportSize({ width: 375, height: 812 });
      await page.locator('#tests > details > summary').first().click();
      await page.locator('#rounds > ol > li > details > summary').first().click();
      check('phone: expanded content stays in viewport', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      const ledger = page.locator('#ledger .table-scroll');
      await ledger.focus();
      await page.keyboard.press('ArrowRight');
      await page.waitForFunction(() => document.querySelector('#ledger .table-scroll').scrollLeft > 0);
      check('phone: keyboard scroll exposes ledger columns', await ledger.evaluate(el => el.scrollWidth > el.clientWidth && el.scrollLeft > 0), true);
      await page.screenshot({ path: path.join(outputRoot, 'phone-repair.png'), fullPage: true });
      await page.setViewportSize({ width: 1200, height: 850 });
    }
    await fs.writeFile(path.join(outputRoot, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  }
  check('no external network requests', report.requests, []);
  check('no application errors', report.applicationErrors, []);
  check('no browser console errors', report.consoleErrors, []);
  await context.close();
  context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 375, height: 812 } });
  const offlinePage = await context.newPage();
  await context.setOffline(true);
  await offlinePage.goto(pathToFileURL(path.join(isolated, 'passed.html')).href);
  await offlinePage.locator('#tests > details > summary').first().click();
  check('offline and JavaScript disabled: generated file expands', await offlinePage.locator('#tests > details pre').first().isVisible(), true);
  check('offline and JavaScript disabled: status', await offlinePage.locator('.status').textContent(), 'passed');
  report.passed = report.checks.filter(x => x.passed).length;
} catch (error) {
  report.failure = String(error.stack || error);
  process.exitCode = 1;
} finally {
  await context?.close();
  await browser.close();
  await fs.writeFile(path.join(outputRoot, 'report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ checks: report.checks.length, passed: report.checks.filter(x => x.passed).length, failure: report.failure }));
}
