'use strict';
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {pathToFileURL} = require('node:url');
const {chromium} = require('/home/jacob/.cache/returnby-backup-8b336fefde84/node_modules/playwright');
const root = '/dev/shm/testpilot-490f-compare';
const out = path.join(root, 'evidence/candidate/browser');
const receipt = {kind:'author native offline-browser qualification',groups:[],downloads:[],externalRequests:[],pageErrors:[]};
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
async function group(name, action) {
  const started=Date.now();
  await action();
  receipt.groups.push({name,passed:true,ms:Date.now()-started});
}
async function row(page, section, label) {
  const rows=page.locator('#'+section+' tbody tr');
  for(let i=0;i<await rows.count();i++){
    const cells=await rows.nth(i).locator('td').allTextContents();
    if(cells[0]===label) return cells;
  }
  throw new Error('Missing row: '+section+'/'+label);
}
async function download(page, id, source, savedName) {
  await page.locator('#'+id).focus();
  const pending=page.waitForEvent('download');
  await page.keyboard.press('Enter');
  const item=await pending;
  assert.equal(await item.failure(),null);
  const saved=path.join(out,savedName);
  await item.saveAs(saved);
  const actual=fs.readFileSync(saved), expected=fs.readFileSync(source);
  assert.deepEqual(actual,expected);
  receipt.downloads.push({id,suggestedFilename:item.suggestedFilename(),source,saved,bytes:actual.length,sha256:hash(actual)});
}
(async()=>{
  let browser;
  try{
    browser=await chromium.launch({executablePath:'/home/jacob/.cache/puppeteer/chrome/linux-154.0.8037.57/chrome-linux64/chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
    receipt.browser=await browser.version();
    const context=await browser.newContext({viewport:{width:1280,height:960},acceptDownloads:true,javaScriptEnabled:false});
    await context.route('**/*',async route=>{
      const u=route.request().url();
      if(!u.startsWith('file:')&&!u.startsWith('data:')){receipt.externalRequests.push(u);await route.abort();}
      else await route.continue();
    });
    const page=await context.newPage();
    page.on('pageerror',error=>receipt.pageErrors.push(String(error)));
    await group('Actual saved bug/fix reports retain recorded status and six-case/four-generated distinction',async()=>{
      await page.goto(pathToFileURL(path.join(root,'evidence/candidate/native-pair-fixed.html')).href);
      assert.deepEqual(await row(page,'results','Recorded status'),['Recorded status','suspected_code_bug','passed']);
      assert.equal((await row(page,'results','Complete-suite recorded counts'))[2],'6 passed, 0 failed, 0 errors, 0 skipped');
      assert.equal((await row(page,'results','Generated-case recorded counts'))[2],'4 collected, 4 passed, 0 failed, 0 error, 0 skipped');
      assert.match(await page.locator('.context').innerText(),/Matching target labels; selected source differs/);
      const fileRows=await page.locator('#files tbody tr').allTextContents();
      assert.equal(fileRows.length,1);
      assert.match(fileRows[0],/unchanged/);
      assert.match(await page.locator('#coverage').innerText(),/Within-run total change/);
      assert.equal(await page.locator('script,iframe,img,object,embed').count(),0);
    });
    await group('Native keyboard navigation and detail toggles work with page JavaScript disabled',async()=>{
      await page.reload();
      await page.keyboard.press('Tab');
      assert.equal(await page.locator(':focus').innerText(),'Skip to recorded results');
      await page.keyboard.press('Enter');
      assert.equal(await page.locator(':focus').getAttribute('id'),'results');
      const summary=page.locator('#source summary').first();
      await summary.focus();
      await page.keyboard.press('Enter');
      assert.equal(await page.locator('#source details').first().getAttribute('open'),'');
      assert.notEqual(await summary.evaluate(e=>getComputedStyle(e).outlineStyle),'none');
      await page.keyboard.press('Space');
      assert.equal(await page.locator('#source details').first().getAttribute('open'),null);
      await download(page,'download-before',path.join(root,'evidence/baseline/before/report.json'),'actual-before-download.json');
      await download(page,'download-after',path.join(root,'evidence/baseline/after/report.json'),'actual-after-download.json');
      await page.goto(pathToFileURL(path.join(root,'evidence/candidate/native-pair-fixed.html')).href);
      await page.screenshot({path:path.join(out,'actual-desktop-fixed.png'),fullPage:false});
    });
    await group('Changed-input literal source and unknown metrics remain explicit while raw formatting survives downloads',async()=>{
      await page.goto(pathToFileURL(path.join(out,'literal-pair-fixed.html')).href);
      const counts=await row(page,'results','Generated-case recorded counts');
      assert.equal(counts[1],'Unavailable as complete execution evidence');
      assert.equal((await row(page,'results','Tests written (reported)'))[1],'731');
      assert.equal((await row(page,'usage','Recorded total cost'))[1],'Unpriced / incomplete');
      assert.equal((await row(page,'coverage','Total before generation'))[1],'Unavailable');
      const body=await page.locator('body').innerText();
      assert.ok(body.includes('<img src="https://saved-literal.invalid/x" onerror="alert(1)"> & </script> "quote"'));
      assert.ok(body.includes('\\u2028'));
      assert.ok(body.includes('\\ud800'));
      assert.equal(await page.locator('script,iframe,img,object,embed').count(),0);
      const files=await page.locator('#files tbody tr').allTextContents();
      assert.ok(files.some(x=>x.includes('tests/test_empty_added.py')&&x.includes('added')&&x.includes('Absent')&&x.endsWith('0')));
      assert.ok(files.some(x=>x.includes('tests/test_literal<&>.py')&&x.includes('added')));
      await download(page,'download-before',path.join(out,'literal-before.json'),'literal-before-download.json');
      await download(page,'download-after',path.join(out,'literal-after.json'),'literal-after-download.json');
    });
    await group('390px layout confines wide tables and source text; touch-size download controls retain native actions',async()=>{
      await page.setViewportSize({width:390,height:844});
      await page.goto(pathToFileURL(path.join(out,'literal-pair-fixed.html')).href);
      const sizes=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
      assert.ok(sizes.scroll<=sizes.width,'page has horizontal overflow: '+JSON.stringify(sizes));
      assert.equal(await page.locator('.columns').first().evaluate(e=>getComputedStyle(e).gridTemplateColumns.split(' ').length),1);
      for(const id of ['download-before','download-after']){
        const box=await page.locator('#'+id).boundingBox();
        assert.ok(box.height>=44);
      }
      await page.screenshot({path:path.join(out,'literal-phone.png'),fullPage:false});
      receipt.mobile=sizes;
    });
    assert.deepEqual(receipt.externalRequests,[]);
    assert.deepEqual(receipt.pageErrors,[]);
    receipt.passed=true;
  }catch(error){
    receipt.passed=false;receipt.error=String(error.stack||error);process.exitCode=1;
  }finally{
    if(browser) await browser.close();
    fs.writeFileSync(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
    console.log(JSON.stringify({passed:receipt.passed,groups:receipt.groups,downloads:receipt.downloads.map(d=>({bytes:d.bytes,sha256:d.sha256})),error:receipt.error||null}));
  }
})();
