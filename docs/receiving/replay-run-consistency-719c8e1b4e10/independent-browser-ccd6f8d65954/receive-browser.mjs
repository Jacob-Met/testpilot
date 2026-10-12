import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import os from 'node:os';
import {spawn} from 'node:child_process';
import {createServer} from 'node:http';

const base=path.resolve(process.argv[2]);
const bundle=JSON.parse(fs.readFileSync(path.join(base,'source-payload.json'),'utf8'));
const contract=bundle.contract, runtime=path.join(base,'runtime'), downloads=path.join(base,'downloads');
fs.mkdirSync(runtime);fs.mkdirSync(downloads);fs.mkdirSync(path.join(base,'captures'));
fs.writeFileSync(path.join(base,'receiving-contract.json'),JSON.stringify(contract,null,2)+'\n');
const hash=(b,algorithm='sha256')=>crypto.createHash(algorithm).update(b).digest('hex');
const blob=b=>hash(Buffer.concat([Buffer.from('blob '+b.length+'\0'),b]),'sha1');
const receipt={schema:'hamon.testpilot.actual-browser-receiving.v1',started_utc:new Date().toISOString(),host:os.hostname(),platform:os.platform(),node:process.version,candidate:contract.candidate,baseline:contract.baseline,source:[],checks:[],downloads:[],captures:[],page_requests:[],server_requests:[],page_errors:[],external_requests:[],limits:contract.limits};
function check(label,value,actual=null){receipt.checks.push({label,passed:!!value,actual});console.log((value?'PASS ':'FAIL ')+label);if(!value)throw new Error('Acceptance failed: '+label);}
for(const expected of contract.source_identities){
 const relative=expected.path.replace(/^web-demo\//,'');
 if(relative===expected.path||relative.split('/').includes('..'))throw new Error('Unsupported source path');
 const file=path.join(runtime,relative), b=Buffer.from(bundle.files[expected.path],'utf8');
 fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,b);
 if(blob(b)!==expected.git_blob)throw new Error('Source blob mismatch: '+expected.path);
 receipt.source.push({path:expected.path,bytes:b.length,sha256:hash(b),git_blob:blob(b)});
}
const baselineApp=Buffer.from(bundle.baseline_app,'utf8');
fs.writeFileSync(path.join(base,'baseline-app.mjs'),baselineApp);
check('28 candidate runtime files match GitHub blobs',receipt.source.length===28);
check('baseline app matches its published blob',blob(baselineApp)===contract.baseline_app_git_blob,blob(baselineApp));
const rawData=fs.readFileSync(path.join(runtime,'data/replays.json')),dataset=JSON.parse(rawData);
function mutated(scenario){
 if(scenario==='healthy')return rawData;
 const d=JSON.parse(rawData);
 if(scenario==='wrong-exit')d.cases[0].runs.baseline.returncode=1;
 else if(scenario==='missing-cases')delete d.cases[1].runs.fixed.cases;
 else if(scenario==='no-failure-witness'){
  const r=d.cases[0].runs.generated;
  r.cases=r.cases.map(c=>({...c,outcome:'passed'}));r.passed=r.cases.length;r.failed=0;
 }else throw new Error('Unknown fixture');
 return Buffer.from(JSON.stringify(d));
}
const mime={'.html':'text/html; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.log':'text/plain; charset=utf-8','.patch':'text/plain; charset=utf-8','.py':'text/plain; charset=utf-8','.diff':'text/plain; charset=utf-8'};
const server=createServer((req,res)=>{
 const u=new URL(req.url,'http://localhost'),m=u.pathname.match(/^\/(candidate|baseline)\/(healthy|wrong-exit|missing-cases|no-failure-witness)\/(.+)$/);
 try{
  if(!m)throw new Error('Unknown receiver path');
  const [,variant,scenario,rel]=m,file=path.resolve(runtime,decodeURIComponent(rel));
  if(!file.startsWith(runtime+path.sep))throw new Error('Outside receiver');
  const b=rel==='app.mjs'&&variant==='baseline'?baselineApp:rel==='data/replays.json'?mutated(scenario):fs.readFileSync(file);
  receipt.server_requests.push({method:req.method,path:u.pathname,status:200,bytes:b.length,sha256:hash(b)});
  res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'});res.end(b);
 }catch(e){receipt.server_requests.push({method:req.method,path:u.pathname,status:404,error:e.message});res.writeHead(404);res.end('No such receiver resource');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin='http://127.0.0.1:'+server.address().port;receipt.origin=origin;
const chrome=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless=new','--remote-debugging-pipe','--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-component-update','--disable-sync','--disable-default-apps','--disable-extensions','--metrics-recording-only','--no-proxy-server','--user-data-dir='+path.join(base,'chrome-profile'),'about:blank'],{stdio:['ignore','pipe','pipe','pipe','pipe']});
receipt.chrome_pid=chrome.pid;
let sid=null,serial=0,buffer=Buffer.alloc(0),stderr='',stdout='';
const pending=new Map(),downloadBegins=[],downloadProgress=new Map();
const exitPromise=new Promise(resolve=>chrome.once('exit',(code,signal)=>resolve({code,signal})));
chrome.stdout.on('data',b=>{stdout+=b;});chrome.stderr.on('data',b=>{stderr+=b;});
function call(method,params={},session=sid){return new Promise((resolve,reject)=>{const id=++serial;const timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout '+method));},12000);pending.set(id,{resolve,reject,timer});chrome.stdio[3].write(JSON.stringify({id,method,params,...(session?{sessionId:session}:{})})+'\0');});}
chrome.stdio[4].on('data',data=>{
 buffer=Buffer.concat([buffer,data]);let n;
 while((n=buffer.indexOf(0))>=0){
  const raw=buffer.subarray(0,n).toString();buffer=buffer.subarray(n+1);if(!raw)continue;
  const msg=JSON.parse(raw);
  if(msg.id){const p=pending.get(msg.id);if(p){pending.delete(msg.id);clearTimeout(p.timer);msg.error?p.reject(new Error(JSON.stringify(msg.error))):p.resolve(msg.result);}continue;}
  if(msg.method==='Runtime.exceptionThrown')receipt.page_errors.push(msg.params);
  if(msg.method==='Network.requestWillBeSent')receipt.page_requests.push({url:msg.params.request.url,type:msg.params.type});
  if(msg.method==='Browser.downloadWillBegin')downloadBegins.push(msg.params);
  if(msg.method==='Browser.downloadProgress')downloadProgress.set(msg.params.guid,msg.params);
  if(msg.method==='Fetch.requestPaused'){
   const url=msg.params.request.url,allowed=url.startsWith(origin+'/')||url.startsWith('data:');
   if(!allowed)receipt.external_requests.push(url);
   call(allowed?'Fetch.continueRequest':'Fetch.failRequest',{requestId:msg.params.requestId,...(allowed?{}:{errorReason:'BlockedByClient'})},msg.sessionId).catch(e=>receipt.page_errors.push({receiver:e.message}));
  }
 }
});
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function evaluate(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
async function snapshot(){return evaluate("({ready:document.getElementById('replay')?.getAttribute('aria-busy'),hidden:document.getElementById('replay')?.hidden,error:document.getElementById('load-error')?.hidden===false?document.getElementById('load-error').textContent:null,caseId:document.getElementById('case-position')?.textContent,stage:[...document.querySelectorAll('#stages button')].findIndex(x=>x.getAttribute('aria-selected')==='true'),focus:document.activeElement?.id,focusCase:document.activeElement?.dataset?.case,text:document.getElementById('stage-content')?.innerText,width:innerWidth,scroll:document.documentElement.scrollWidth,url:location.href,downloads:['download-patch','download-record','download-log'].map(id=>{const x=document.getElementById(id);return {id,href:x?.getAttribute('href'),disabled:x?.getAttribute('aria-disabled')}})})");}
async function open(variant='candidate',scenario='healthy',query='',width=1440,height=1000){
 await call('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
 const nav=await call('Page.navigate',{url:origin+'/'+variant+'/'+scenario+'/index.html'+query});if(nav.errorText)throw new Error(nav.errorText);
 for(let i=0;i<150;i++){const s=await snapshot();if((s.ready==='false'&&!s.hidden)||s.error)return s;await pause(30);}
 throw new Error('Page did not reach a ready or refused state');
}
async function pointer(selector){
 const pos=await evaluate("(()=>{const e=document.querySelector("+JSON.stringify(selector)+");if(!e)throw new Error('Missing target');e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,width:r.width,height:r.height};})()");
 if(!pos.width||!pos.height)throw new Error('Hidden pointer target: '+selector);
 await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:pos.x,y:pos.y});
 await call('Input.dispatchMouseEvent',{type:'mousePressed',x:pos.x,y:pos.y,button:'left',clickCount:1});
 await call('Input.dispatchMouseEvent',{type:'mouseReleased',x:pos.x,y:pos.y,button:'left',clickCount:1});
 return snapshot();
}
async function press(key){
 const codes={Tab:9,Enter:13,ArrowRight:39,ArrowLeft:37,Home:36,End:35};
 const params={key,code:key,windowsVirtualKeyCode:codes[key],nativeVirtualKeyCode:codes[key]};
 await call('Input.dispatchKeyEvent',{type:'keyDown',...params});await call('Input.dispatchKeyEvent',{type:'keyUp',...params});return snapshot();
}
async function download(id,filename,item,view){
 const before=downloadBegins.length;await pointer('#'+id);
 let event;
 for(let i=0;i<200;i++){event=downloadBegins[before];if(event&&downloadProgress.get(event.guid)?.state==='completed')break;await pause(25);}
 if(!event||downloadProgress.get(event.guid)?.state!=='completed')throw new Error('Actual download did not complete: '+filename);
 const b=fs.readFileSync(path.join(downloads,event.guid)),observed={view,case:item.id,filename,suggested:event.suggestedFilename,guid:event.guid,bytes:b.length,sha256:hash(b),browser_state:downloadProgress.get(event.guid).state};
 receipt.downloads.push(observed);
 check(view+'/'+item.id+': exact native '+filename+' download',observed.bytes===item.files[filename].bytes&&observed.sha256===item.files[filename].sha256&&observed.suggested===item.id+'-'+filename,observed);
}
async function capture(file){
 await evaluate('window.scrollTo(0,0)');await pause(60);
 const m=await call('Page.getLayoutMetrics'),clip={x:0,y:0,width:m.cssContentSize.width,height:m.cssContentSize.height,scale:1};
 const r=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip});
 const b=Buffer.from(r.data,'base64');fs.writeFileSync(path.join(base,'captures',file),b);
 receipt.captures.push({file,bytes:b.length,sha256:hash(b),width:clip.width,height:clip.height});
}
try{
 receipt.browser=await call('Browser.getVersion',{},null);
 await call('Browser.setDownloadBehavior',{behavior:'allowAndName',downloadPath:downloads,eventsEnabled:true},null);
 const t=await call('Target.createTarget',{url:'about:blank'},null);sid=(await call('Target.attachToTarget',{targetId:t.targetId,flatten:true},null)).sessionId;
 await call('Page.enable');await call('Runtime.enable');await call('Network.enable');await call('Fetch.enable',{patterns:[{urlPattern:'*'}]});
 for(const view of [{name:'desktop',width:1440,height:1000},{name:'390px',width:390,height:844}]){
  let s=await open('candidate','healthy','',view.width,view.height);
  check(view.name+': honest recorded-evidence disclosure',await evaluate("document.querySelector('.disclosure').innerText.includes('ScriptedModel')&&document.querySelector('.disclosure').innerText.includes('No live model calls')"));
  await press('Tab');check(view.name+': keyboard skip link receives focus',await evaluate("document.activeElement.classList.contains('skip-link')"));
  await press('Enter');check(view.name+': skip link reaches replay',(await snapshot()).focus==='stage-content');
  for(const item of dataset.cases){
   s=await pointer('[data-case="'+item.id+'"]');check(view.name+'/'+item.id+': fixture starts at diff with focus',s.caseId===item.id&&s.stage===0&&s.focusCase===item.id,s);
   for(let stage=0;stage<4;stage++){
    s=await snapshot();check(view.name+'/'+item.id+': stage '+(stage+1)+' ready and fits',s.stage===stage&&!s.hidden&&!s.error&&s.scroll<=view.width,{stage:s.stage,scroll:s.scroll,width:view.width});
    if(stage===2)check(view.name+'/'+item.id+': actual recorded result is visible',s.text.includes(item.runs.generated.output.trim())&&s.text.includes(item.kind==='caught'?'Code bug suspected':'boundary still untested'));
    if(stage<3)await pointer('#next');
   }
   s=await snapshot();check(view.name+'/'+item.id+': separate oracle witness is visible',s.text.includes('Boundary witness')&&s.text.includes(item.witness.trim()));
   for(const [id,file] of [['download-patch','testpilot.patch'],['download-record','record.json'],['download-log','generated.log']])await download(id,file,item,view.name);
   if(item.id==='stats_median')await capture(view.name==='desktop'?'desktop-oracle.png':'narrow-oracle.png');
  }
  await pointer('#stage-tab-0');s=await press('ArrowRight');check(view.name+': arrow key switches and focuses stage',s.stage===1&&s.focus==='stage-tab-1');
  s=await press('End');check(view.name+': End reaches oracle',s.stage===3&&s.focus==='stage-tab-3');
  s=await press('Home');check(view.name+': Home returns to diff',s.stage===0&&s.focus==='stage-tab-0');
  s=await open('candidate','healthy','?case=stats_median&stage=4',view.width,view.height);check(view.name+': saved fixture/stage URL reopens exactly',s.caseId==='stats_median'&&s.stage===3);
  s=await open('candidate','healthy','?case=missing&stage=99',view.width,view.height);check(view.name+': invalid deep link uses stable initial view',s.caseId==='calc_clamp'&&s.stage===0);
 }
 for(const scenario of ['wrong-exit','missing-cases','no-failure-witness']){
  const original=await open('baseline',scenario,'?case=calc_clamp&stage=3');
  check('baseline reproduction admits '+scenario,!original.hidden&&!original.error&&original.stage===2&&original.downloads.every(x=>x.href&&x.disabled===null),original);
  const candidate=await open('candidate',scenario,'?case=calc_clamp&stage=3');
  check('candidate refuses '+scenario+' before verdict or downloads',candidate.hidden&&candidate.error?.includes('A required fixture run')&&candidate.downloads.every(x=>x.href===null&&x.disabled==='true'),candidate);
 }
 const recovered=await open();check('fresh healthy reload recovers after refusal',!recovered.hidden&&!recovered.error&&recovered.stage===0&&recovered.downloads.every(x=>x.href&&x.disabled===null));
 check('no external page request attempted',receipt.external_requests.length===0,receipt.external_requests);
 check('no page exception',receipt.page_errors.length===0,receipt.page_errors);
 const unchanged=receipt.source.every(x=>hash(fs.readFileSync(path.join(runtime,x.path.replace(/^web-demo\//,''))))===x.sha256);
 check('all candidate runtime files unchanged after receiving',unchanged);
 check('baseline source unchanged after receiving',blob(fs.readFileSync(path.join(base,'baseline-app.mjs')))===contract.baseline_app_git_blob);
}catch(error){receipt.fatal={message:error.message,stack:error.stack};console.error(error.stack);}
finally{
 try{await call('Browser.close',{},null);chrome.stdio[3].end();}catch(e){receipt.browser_close_error=e.message;}
 receipt.chrome_exit=await Promise.race([exitPromise,pause(10000).then(()=>null)]);
 if(!receipt.chrome_exit){chrome.kill('SIGTERM');receipt.termination_requested=true;receipt.exit_after_termination=await Promise.race([exitPromise,pause(3000).then(()=>null)]);}
 for(const p of pending.values())clearTimeout(p.timer);pending.clear();
 for(const stream of chrome.stdio)if(stream?.destroy)stream.destroy();
 server.closeAllConnections();await new Promise(resolve=>server.close(resolve));receipt.server_closed=server.address()===null;
 fs.writeFileSync(path.join(base,'chrome.stderr.log'),stderr);fs.writeFileSync(path.join(base,'chrome.stdout.log'),stdout);
 receipt.finished_utc=new Date().toISOString();receipt.passed=receipt.checks.filter(x=>x.passed).length;receipt.failed=receipt.checks.filter(x=>!x.passed).length;
 receipt.success=!receipt.fatal&&receipt.failed===0&&receipt.chrome_exit?.code===0&&receipt.server_closed;
 fs.writeFileSync(path.join(base,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
 console.log(JSON.stringify({receipt:path.join(base,'receipt.json'),passed:receipt.passed,failed:receipt.failed,success:receipt.success,downloads:receipt.downloads.length,chrome_exit:receipt.chrome_exit,server_closed:receipt.server_closed,fatal:receipt.fatal}));
 process.exitCode=receipt.success?0:1;
}
