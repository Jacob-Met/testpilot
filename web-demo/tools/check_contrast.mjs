// SPDX-License-Identifier: Apache-2.0
// Native Chromium receiving for two-fixture contrast; preserves actual-page evidence.
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = path.resolve(process.argv[2] || new URL('..', import.meta.url).pathname);
const output = path.resolve(process.argv[3] || path.join(root, 'receipts/contrast'));
const moduleName = process.env.TESTPILOT_PLAYWRIGHT_MODULE || 'playwright';
const { chromium } = await import(path.isAbsolute(moduleName) ? pathToFileURL(moduleName).href : moduleName);
const dataset = JSON.parse(await readFile(path.join(root, 'data/replays.json'), 'utf8'));
await mkdir(output, {recursive:true});
const cases = dataset.cases;
const checks = []; const errors = []; const external = [];
function check(label, value) {
  const ok = Boolean(value);
  checks.push({label,ok});
  assert.ok(ok, label);
}
const mime = {'.html':'text/html','.css':'text/css','.mjs':'text/javascript','.json':'application/json','.txt':'text/plain','.py':'text/plain','.patch':'text/plain','.log':'text/plain'};
const server = createServer(async (req,res) => {
  try {
    const url = new URL(req.url, 'http://localhost');
    const rel = decodeURIComponent(url.pathname).replace(/^\/+/, '') || 'index.html';
    const dest = path.resolve(root,rel);
    if (!dest.startsWith(root + path.sep)) throw new Error('outside');
    const body = await readFile(dest);
    res.writeHead(200, {'content-type':mime[path.extname(dest)]||'application/octet-stream','cache-control':'no-store'});
    res.end(body);
  } catch { res.writeHead(404);res.end('Not found'); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = 'http://127.0.0.1:' + server.address().port;
const options = {headless:true};
if (process.env.TESTPILOT_BROWSER_EXECUTABLE) options.executablePath = process.env.TESTPILOT_BROWSER_EXECUTABLE;
let browser, failure;
try {
  browser = await chromium.launch(options);
  for (const vp of [{name:'desktop',width:1440,height:1000},{name:'phone',width:390,height:844}]) {
    const context = await browser.newContext({viewport:{width:vp.width,height:vp.height},reducedMotion:'reduce'});
    await context.route('**/*', route => {
      const url = route.request().url();
      if (url.startsWith(origin + '/') || url.startsWith('data:') || url.startsWith('blob:')) return route.continue();
      external.push(url); return route.abort();
    });
    const page = await context.newPage();
    page.on('pageerror',e=>errors.push(String(e)));
    await page.goto(origin+'/contrast.html?ref=lab');
    await page.locator('#contrast[aria-busy="false"]').waitFor();
    check(vp.name+': no validation failure', await page.locator('#load-error').isHidden());
    check(vp.name+': source pin visible', (await page.locator('#capture-source').innerText()).includes(dataset.source.commit.slice(0,12)));
    check(vp.name+': two independently attributed outcomes', await page.locator('.evidence-lane.caught').count()===1 && await page.locator('.evidence-lane.missed').count()===1);
    check(vp.name+': distinct default fixture positions', await page.locator('.evidence-lane').first().getAttribute('data-fixture')===cases[0].id &&
      await page.locator('.evidence-lane').last().getAttribute('data-fixture')===cases[1].id);
    check(vp.name+': no viewport overflow', await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    check(vp.name+': diff exact retained evidence for both sides',
      await page.locator('.evidence-lane').first().innerText().then(x=>x.includes(cases[0].bug)) &&
      await page.locator('.evidence-lane').last().innerText().then(x=>x.includes(cases[1].bug)));
    await page.locator('#next').click();
    check(vp.name+': generated tests stage for both fixtures', await page.locator('#stage-tab-1').getAttribute('aria-selected')==='true' &&
      await page.locator('.evidence-lane .evidence-section pre').count()>=4);
    await page.locator('#next').click();
    const execution = await page.locator('#comparison').innerText();
    check(vp.name+': accurate generated-run distinction', execution.includes(cases[0].runs.generated.output.trim()) &&
      execution.includes(cases[1].runs.generated.output.trim()) &&
      execution.includes('FAILURE IS USEFUL EVIDENCE') && execution.includes('A GREEN RESULT IS NOT PROOF'));
    await page.locator('#next').click();
    const oracle = await page.locator('#comparison').innerText();
    check(vp.name+': independent controls and original witness bytes visible', oracle.includes(cases[0].witness.trim()) &&
      oracle.includes(cases[1].witness.trim()) && oracle.includes('BLIND SPOT REVEALED') && oracle.includes('REGRESSION EXPOSED'));
    check(vp.name+': link targets each verified replay stage', (await page.locator('#open-left').getAttribute('href')).includes('stage=4') &&
      (await page.locator('#open-right').getAttribute('href')).includes(cases[1].id));
    await page.locator('.evidence-lane').first().locator('.witness-traces summary').click();
    check(vp.name+': original independent changed-code pytest is inspectable',
      (await page.locator('.evidence-lane').first().locator('.witness-traces').innerText())
        .includes(cases[0].runs.witness_buggy.output.trim()));
    check(vp.name+': original independent fixed-code pytest is inspectable',
      (await page.locator('.evidence-lane').first().locator('.witness-traces').innerText())
        .includes(cases[0].runs.witness_fixed.output.trim()));
    check(vp.name+': no terminal next advance', await page.locator('#next').isDisabled());
    check(vp.name+': terminal stage fits viewport', await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(output,vp.name+'-oracle.png'),fullPage:true});
    await page.locator('#swap').click();
    check(vp.name+': swap retained stage and switched fixtures',
      await page.locator('.evidence-lane').first().getAttribute('data-fixture')===cases[1].id &&
      new URL(page.url()).searchParams.get('left')===cases[1].id &&
      await page.locator('#stage-tab-3').getAttribute('aria-selected')==='true');
    check(vp.name+': unrelated URL query preserved',new URL(page.url()).searchParams.get('ref')==='lab');
    await page.goBack();
    check(vp.name+': browser Back restores original side order',await page.locator('.evidence-lane').first().getAttribute('data-fixture')===cases[0].id);
    await page.goForward();
    check(vp.name+': browser Forward restores swapped side order',await page.locator('.evidence-lane').first().getAttribute('data-fixture')===cases[1].id);
    await page.locator('#open-left').click();
    await page.locator('#replay[aria-busy="false"]').waitFor();
    await page.locator('#integrity-status[data-state="verified"]').waitFor();
    check(vp.name+': opens the exact SHA-verified single replay',
      await page.locator('[data-case="'+cases[1].id+'"][aria-pressed="true"]').count()===1 &&
      await page.locator('#stage-tab-3[aria-selected="true"]').count()===1 &&
      (await page.locator('#integrity-status').innerText()).includes('4/4'));
    await page.goBack();
    await page.locator('#contrast[aria-busy="false"]').waitFor();
    await page.locator('#stage-tab-3').focus(); await page.keyboard.press('Home');
    check(vp.name+': keyboard Home',await page.locator('#stage-tab-0[aria-selected="true"]').count()===1);
    await page.keyboard.press('ArrowRight');
    check(vp.name+': keyboard ArrowRight focus and selection',
      await page.locator('#stage-tab-1[aria-selected="true"]').count()===1 &&
      await page.evaluate(()=>document.activeElement.id)==='stage-tab-1');
    await page.goto(origin+'/contrast.html?left=unknown&right=unknown&stage=999');
    await page.locator('#contrast[aria-busy="false"]').waitFor();
    check(vp.name+': malformed deep link deterministic distinct fallback',
      await page.locator('.evidence-lane').first().getAttribute('data-fixture')===cases[0].id &&
      await page.locator('.evidence-lane').last().getAttribute('data-fixture')===cases[1].id &&
      await page.locator('#stage-tab-0[aria-selected="true"]').count()===1);
    await page.goto(origin+'/');
    await page.locator('#replay[aria-busy="false"]').waitFor();
    check(vp.name+': comparison discoverable from original replay', await page.locator('a.contrast-entry').count()===1);
    await page.locator('a.contrast-entry').click();
    await page.locator('#contrast[aria-busy="false"]').waitFor();
    check(vp.name+': native replay entry opens contrast',page.url().includes('/contrast.html'));
    await context.close();
  }
  const broken = await browser.newContext();
  await broken.route('**/data/replays.json', route => {
    const changed = structuredClone(dataset);
    changed.cases[1].kind = 'caught';
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(changed)});
  });
  const page = await broken.newPage();
  page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(origin+'/contrast.html');
  await page.locator('#contrast[aria-busy="false"]').waitFor();
  check('contradictory recorded outcome is visibly refused',
    await page.locator('#load-error').isVisible() && await page.locator('.evidence-lane').count()===0 &&
    (await page.locator('#load-error').innerText()).includes('contradicts'));
  await broken.close();
  // Changed-input control: a recorded "green" verdict must agree with test counts.
  const incoherent = await browser.newContext();
  await incoherent.route('**/data/replays.json', route => {
    const changed = structuredClone(dataset);
    changed.cases[1].runs.generated.passed = 0;
    changed.cases[1].runs.generated.failed = 5;
    // The claim remains "ok": the exact contradiction this verifier must refuse.
    return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(changed)});
  });
  const numericPage = await incoherent.newPage();
  numericPage.on('pageerror', e => errors.push(String(e)));
  await numericPage.goto(origin+'/contrast.html');
  await numericPage.locator('#contrast[aria-busy="false"]').waitFor();
  check('contradictory green verdict and failed counts is visibly refused',
    await numericPage.locator('#load-error').isVisible() &&
    await numericPage.locator('.evidence-lane').count()===0);
  await incoherent.close();
  check('no remote browser requests',external.length===0);
  check('no page-script exceptions',errors.length===0);
} catch(err) {failure=String(err.stack||err);}
finally {
  if (browser) await browser.close();
  await new Promise(resolve=>server.close(resolve));
  const receipt={source_commit:dataset.source.commit,checks,errors,external,failed:failure||null};
  await writeFile(path.join(output,'contrast-receipt.json'),JSON.stringify(receipt,null,2));
  console.log(JSON.stringify({passed:checks.filter(x=>x.ok).length,total:checks.length,failed:failure||null,errors,external},null,2));
}
if(failure) process.exitCode=1;
