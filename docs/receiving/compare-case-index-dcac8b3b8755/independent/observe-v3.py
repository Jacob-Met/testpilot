"""Independent original-first saved-comparison receiving; own inputs and outputs only."""
import argparse, base64, getpass, hashlib, json, os, pathlib, re, subprocess, sys, time, traceback
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(r'D:\hamon-dcac8b3b8755-testpilot-failure-index-v1')
CHROME = r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
def identity(path):
    data=path.read_bytes(); st=path.stat()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
            'git_blob':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),
            'mode':str(st.st_mode),'mtime_ns':str(st.st_mtime_ns),'inode':str(st.st_ino)}
def inventory(root):
    return {p.relative_to(root).as_posix():identity(p) for p in sorted(root.rglob('*')) if p.is_file()}
def dump(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
def check(receipt,name,actual,expected):
    passed=actual==expected
    receipt['checks'].append({'name':name,'actual':actual,'expected':expected,'passed':passed})
    if not passed: raise AssertionError(name)
def diagnostics(page):
    return page.locator('#diagnostics > .columns > div').evaluate_all('''columns => columns.flatMap((column, side) => [...column.querySelectorAll(':scope > details')].slice(0,-1).map((d,index) => ({role:side===0?'before':'after',position:index+1,id:d.id,open:d.open,summary:d.querySelector('summary').textContent,label:d.querySelector('summary').textContent.slice(d.querySelector('.pill').textContent.length),outcome:d.querySelector('.pill').textContent,message:d.querySelector('pre code')?.textContent ?? null})))''')
def states(page):
    return page.locator('details').evaluate_all('nodes => nodes.map(d=>d.open)')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['original','candidate']);args=ap.parse_args();phase=args.phase
    intake=ROOT/('intake-'+phase+'.json'); packet=json.loads(intake.read_bytes())
    assert packet['phase']==phase
    criteria=packet['criteria']; expected=criteria['expectations']
    run=ROOT/(phase+'-course-v3'); run.mkdir(exist_ok=False)
    source=run/'source';source.mkdir(); fixtures=run/'fixtures';fixtures.mkdir()
    receipt={'schema':'hamon.testpilot-failure-index-browser/1','phase':phase,'started':datetime.now(timezone.utc).isoformat(),'passed':False,'checks':[],'requests':[],'errors':[],'downloads':[]}
    context=None; browser=None; pw=None; disconnected=[]; preserve=[]
    try:
        check(receipt,'selected device account',[os.name,getpass.getuser()],['nt','Veria'])
        for f in packet['source']['files']:
            path=source/f['path'];path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as stream:stream.write(f['content'].encode('utf-8'))
            actual=identity(path);check(receipt,'admitted '+f['path'],[actual[k] for k in ('bytes','sha256','git_blob')],[f[k] for k in ('bytes','sha256','git_blob')])
        for f in packet['fixtures']:
            path=fixtures/f['path']
            with path.open('xb') as stream:stream.write(base64.b64decode(f['base64'],validate=True))
            actual=identity(path);check(receipt,'admitted '+f['path'],[actual[k] for k in ('bytes','sha256','git_blob')],[f[k] for k in ('bytes','sha256','git_blob')])
        preserve=[intake,ROOT/'criteria.json',pathlib.Path(__file__).resolve(),ROOT/'receive_browser.py',ROOT/'receive_browser_v2.py']
        preserve.extend(p for p in (ROOT/'original-course').rglob('*') if p.is_file() and 'profile' not in p.parts)
        preserve.extend(p for p in (ROOT/'original-course-v2').rglob('*') if p.is_file() and not {'profile','browser-downloads'}.intersection(p.parts))
        if phase=='candidate':
            original=ROOT/'original-course-v3'/'receiving.json';old=json.loads(original.read_bytes())
            check(receipt,'original course closed before candidate',[old['phase'],old['passed']],['original',True])
            preserve.extend(p for p in (ROOT/'original-course-v3').rglob('*') if p.is_file() and not {'profile','browser-downloads'}.intersection(p.parts))
        receipt['source_before']=inventory(source);receipt['fixtures_before']=inventory(fixtures)
        receipt['witness_before']={str(p):identity(p) for p in preserve}
        output=run/'comparison.html'
        argv=[sys.executable,'-B','-m','testpilot','compare','--before',str(fixtures/'before.json'),'--after',str(fixtures/'after.json'),'--out',str(output)]
        env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','COMSPEC','PATH','PATHEXT','TEMP','TMP','USERPROFILE'}}
        env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONUTF8']='1';env['TEMP']=str(run);env['TMP']=str(run)
        child=subprocess.Popen(argv,cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:stdout,stderr=child.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            child.kill();stdout,stderr=child.communicate();raise AssertionError('owned CLI timed out')
        (run/'producer.stdout').write_bytes(stdout);(run/'producer.stderr').write_bytes(stderr)
        receipt['producer']={'argv':argv,'pid':child.pid,'exit':child.returncode,'cwd':str(source),'python':sys.version}
        check(receipt,'ordinary compare CLI exit',child.returncode,0);check(receipt,'ordinary compare CLI stderr',stderr.decode('utf-8'),'')
        receipt['html_before']=identity(output)
        downloads_path=run/'browser-downloads';downloads_path.mkdir()
        receipt['browser_scratch']={'downloads_path':str(downloads_path),'context':'nonpersistent','browser_os_exit':'not measured'}
        pw=sync_playwright().start()
        browser=pw.chromium.launch(executable_path=CHROME,downloads_path=str(downloads_path),headless=True,args=['--no-first-run','--no-default-browser-check'])
        context=browser.new_context(java_script_enabled=False,accept_downloads=True,viewport={'width':1280,'height':900})
        if browser:browser.on('disconnected',lambda:disconnected.append(True))
        page=context.pages[0] if context.pages else context.new_page()
        page.on('request',lambda req:receipt['requests'].append({'url':req.url,'method':req.method}))
        page.on('pageerror',lambda error:receipt['errors'].append(str(error)))
        page.on('console',lambda msg:receipt['errors'].append('console: '+msg.text) if msg.type=='error' else None)
        page.goto(output.as_uri(),wait_until='load',timeout=30000)
        receipt['browser']={'version':browser.version if browser else None,'javascript_enabled':False,'executable':CHROME}
        check(receipt,'no document scripts',page.locator('script').count(),0)
        actual=diagnostics(page);dump(run/'initial-diagnostics.json',actual)
        check(receipt,'all retained diagnostic occurrences',[{k:d[k] for k in ('role','position','outcome','label','message','open')} for d in actual],expected)
        results=page.locator('#results').inner_text();check(receipt,'incomplete JUnit retained',results.count('Unavailable as complete execution evidence'),4)
        links=page.locator('#diagnostics a[href^="#"]');check(receipt,'failure index size',links.count(),criteria[phase+'_index_count'])
        if phase=='original':
            check(receipt,'original case identities absent',[d['id'] for d in actual],['']*len(expected))
        else:
            targets=[]
            for i,occurrence in enumerate(criteria['index_occurrences']):
                link=links.nth(i);href=link.get_attribute('href');target_id=href[1:]
                check(receipt,'fixed target format '+str(i),bool(re.fullmatch(r'[a-z][a-z0-9-]*',target_id)),True)
                target=page.locator('details[id="'+target_id+'"]');check(receipt,'unique target '+str(i),target.count(),1)
                target_record=next(d for d in actual if d['id']==target_id)
                check(receipt,'correct retained occurrence '+str(i),[target_record['role'],target_record['position']],occurrence)
                check(receipt,'fixed role and retained position identity '+str(i),['-'+target_record['role']+'-' in target_id,target_id.endswith('-'+str(target_record['position']))],[True,True])
                label=link.inner_text()
                check(receipt,'literal label in index '+str(i),target_record['label'] in label,True)
                check(receipt,'index identifies role position outcome '+str(i),[
                    bool(re.search(r'(?<![A-Za-z])'+target_record['role']+r'(?![A-Za-z])',label.lower())),
                    bool(re.search(r'(?<![0-9])'+str(target_record['position'])+r'(?![0-9])',label)),
                    target_record['outcome'] in label.lower()], [True,True,True])
                targets.append(target_id)
            check(receipt,'all index targets distinct',len(set(targets)),6)
            first=page.locator('details[id="'+targets[0]+'"] > summary');first.click()
            check(receipt,'manual failure collapse',page.locator('details[id="'+targets[0]+'"]').evaluate('d=>d.open'),False)
            prior=states(page)
            for i,target_id in enumerate(targets):
                links.nth(i).click();check(receipt,'native fragment '+str(i),page.evaluate('location.hash'),'#'+target_id)
                check(receipt,'navigation keeps disclosure state '+str(i),states(page),prior)
                check(receipt,'target summary in viewport '+str(i),page.locator('details[id="'+target_id+'"] > summary').evaluate('e=>{const r=e.getBoundingClientRect();return r.top>=0 && r.top<innerHeight && r.bottom>0}'),True)
            page.locator('nav[aria-label="Report sections"] a[href="#diagnostics"]').click()
            links.last.focus();links.last.press('Enter')
            check(receipt,'keyboard native fragment',page.evaluate('location.hash'),'#'+targets[-1]);check(receipt,'keyboard disclosure conservation',states(page),prior)
            receipt['targets']=targets
        for role in ('before','after'):
            with page.expect_download(timeout=10000) as pending:page.locator('#download-'+role).click()
            download=pending.value;dest=run/(role+'-download.json')
            receipt.setdefault('download_events',[]).append({'role':role,'suggested_filename':download.suggested_filename,'failure':download.failure()})
            download.save_as(str(dest))
            check(receipt,role+' original download name',download.suggested_filename,role+'-report.json')
            check(receipt,role+' actual download bytes',dest.read_bytes()==(fixtures/(role+'.json')).read_bytes(),True)
            receipt['downloads'].append({'role':role,'name':download.suggested_filename,**identity(dest)})
        page.set_viewport_size({'width':390,'height':844})
        page.locator('nav[aria-label="Report sections"] a[href="#diagnostics"]').click()
        check(receipt,'390px document fits',page.evaluate('document.documentElement.scrollWidth'),390)
        if phase=='candidate':
            check(receipt,'index has no horizontal overflow',links.evaluate_all('nodes => nodes.every(a=>a.getBoundingClientRect().left>=0 && a.getBoundingClientRect().right<=innerWidth)'),True)
        page.screenshot(path=str(run/'diagnostics-390.png'))
        page.set_viewport_size({'width':1280,'height':900});page.locator('nav[aria-label="Report sections"] a[href="#diagnostics"]').click();page.screenshot(path=str(run/'diagnostics-desktop.png'))
        page.emulate_media(media='print')
        check(receipt,'print media retains every diagnostic', [{k:d[k] for k in ('role','position','outcome','label','message')} for d in diagnostics(page)], [{k:d[k] for k in ('role','position','outcome','label','message')} for d in expected])
        check(receipt,'print media exposes all diagnostic bodies',page.locator('#diagnostics .detail').evaluate_all('nodes=>nodes.every(e=>e.getBoundingClientRect().height>0)'),True)
        page.emulate_media(media='screen')
        check(receipt,'external requests', [r for r in receipt['requests'] if not r['url'].startswith('file:')],[])
        check(receipt,'browser errors',receipt['errors'],[])
        check(receipt,'browser storage empty',context.storage_state(),{'cookies':[],'origins':[]})
        receipt['passed']=True
    except Exception as exc:
        receipt['exception']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        if context:
            try:context.close()
            except Exception as exc:receipt['cleanup_error']=str(exc);receipt['passed']=False
        if browser:
            try:browser.close()
            except Exception as exc:receipt['browser_cleanup_error']=str(exc);receipt['passed']=False
        if pw:
            try:pw.stop()
            except Exception as exc:receipt['playwright_cleanup_error']=str(exc);receipt['passed']=False
        try:
            if browser:check(receipt,'managed browser disconnected',bool(disconnected),True)
            if 'source_before' in receipt:
                receipt['source_after']=inventory(source);receipt['fixtures_after']=inventory(fixtures);receipt['witness_after']={str(p):identity(p) for p in preserve};receipt['html_after']=identity(output)
                for label in ('source','fixtures','witness','html'):check(receipt,label+' conservation',receipt[label+'_after'],receipt[label+'_before'])
        except Exception as exc:receipt['conservation_error']=str(exc);receipt['passed']=False
        receipt['finished']=datetime.now(timezone.utc).isoformat();dump(run/'receiving.json',receipt)
        print(json.dumps({'phase':phase,'passed':receipt['passed'],'checks':len(receipt['checks']),'receipt':identity(run/'receiving.json'),'exception':receipt.get('exception')}),flush=True)
    return 0 if receipt['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
