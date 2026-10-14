"""Original-first passive TestPilot generated-source download receiving."""
from pathlib import Path
import argparse, base64, datetime, hashlib, importlib.metadata, json, os, platform, sys, tempfile, traceback
from playwright.sync_api import sync_playwright

def ident(b):
    return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),
            'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}

def snap(root):
    result={}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():raise ValueError('admitted link')
        if p.is_file():
            s=p.stat();result[p.relative_to(root).as_posix()]={**ident(p.read_bytes()),'mode':s.st_mode,'mtime_ns':str(s.st_mtime_ns),'inode':str(s.st_ino)}
    return result

FIXED = """() => ({
 title:document.title,
 csp:document.querySelector('meta[http-equiv="Content-Security-Policy"]').content,
 sections:Object.fromEntries(['results','source','diagnostics','coverage','usage','rounds','originals'].map(id=>{
   const x=document.getElementById(id).cloneNode(true);x.querySelectorAll('details').forEach(d=>d.removeAttribute('open'));return[id,x.innerHTML];})),
 fileTable:[...document.querySelectorAll('#files tbody tr')].map(x=>[...x.querySelectorAll('td')].map(t=>t.textContent)),
 files:[...document.querySelectorAll('#files details[id^="file-"]')].map(x=>({
   id:x.id,summary:x.querySelector('summary').textContent,
   headings:[...x.querySelectorAll('h3')].map(t=>t.textContent),
   pre:[...x.querySelectorAll('pre')].map(t=>({label:t.getAttribute('aria-label'),text:t.textContent})),
   absent:[...x.querySelectorAll('p.empty')].map(t=>t.textContent),
   omitted:[...x.querySelectorAll('p.note')].map(t=>t.textContent).filter(t=>t.startsWith('Inline diff omitted'))})),
 originals:[...document.querySelectorAll('#originals a[download]')].map(x=>({id:x.id,label:x.textContent,name:x.download,href:x.getAttribute('href')})),
 index:[...document.querySelectorAll('nav.case-index a')].map(x=>({href:x.getAttribute('href'),text:x.textContent}))})"""
STORAGE = """() => Object.fromEntries(['localStorage','sessionStorage'].map(k=>{try{return[k,Object.fromEntries(Object.entries(window[k]))];}catch(e){return[k,{unavailable:e.name}];}}))"""

def main():
    ap=argparse.ArgumentParser()
    for n in ['inputs','output']:ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--chrome',required=True);ap.add_argument('--source',required=True)
    ap.add_argument('--mode',choices=['original','candidate'],required=True);a=ap.parse_args()
    inp=a.inputs.resolve();out=a.output.resolve();out.mkdir(exist_ok=False)
    temp=out.parent/(out.name+'-process-temp');temp.mkdir(exist_ok=False);downloads=temp/'downloads';downloads.mkdir()
    os.environ['TEMP']=os.environ['TMP']=str(temp);tempfile.tempdir=str(temp)
    r={'schema':'hamon.testpilot130.browser/1','mode':a.mode,'source':a.source,
       'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runtime':{'python':sys.version,'playwright':importlib.metadata.version('playwright'),'host':platform.node(),'user':os.environ.get('USERNAME'),'chrome':a.chrome,'chromium_sandbox':True},
       'checks':[],'downloads':[],'fixed':{},'requests':[],'page_errors':[],'passed':False,'managed_disconnect':False,
       'scope':'Passive fictional saved comparisons only; no generated source/test/model/provider execution. Print media and managed disconnect only, not physical print/PDF or separately measured OS Chrome exit.'}
    pw=browser=context=None;r['before']=snap(inp)
    def check(name,actual,expected):
        r['checks'].append({'name':name,'actual':actual,'expected':expected,'passed':actual==expected})
        if actual!=expected:raise RuntimeError(name)
    def save(page,anchor,filename,expected,record,keyboard=False):
        check(record+' unique link',anchor.count(),1);check(record+' native filename',anchor.get_attribute('download'),filename)
        check(record+' visible action',anchor.is_visible(),True)
        if keyboard:
            anchor.evaluate('(x)=>x.scrollIntoView({block:"center"})');anchor.focus();page.keyboard.press('Shift+Tab');page.keyboard.press('Tab')
            check(record+' native Tab focus',anchor.evaluate('(x)=>document.activeElement===x'),True)
            with page.expect_download(timeout=15000) as event:page.keyboard.press('Enter')
        else:
            with page.expect_download(timeout=15000) as event:anchor.click()
        dl=event.value;check(record+' suggested filename',dl.suggested_filename,filename)
        check(record+' download failure',dl.failure(),None)
        p=out/(record+'-'+filename);dl.save_as(str(p));actual=p.read_bytes()
        check(record+' saved identity',ident(actual),ident(expected));check(record+' whole bytes',actual==expected,True)
        r['downloads'].append({'record':record,'path':p.name,**ident(actual)})
    try:
        raw=(inp/'criteria.json').read_bytes();rules=json.loads(raw);r['criteria']=ident(raw)
        raw=(inp/'producer.json').read_bytes();producer=json.loads(raw);r['producer']=ident(raw)
        raw=(inp/'source-packet.json').read_bytes();packet=json.loads(raw);r['packet']=ident(raw)
        baseline=json.loads((inp/'baseline.json').read_bytes()) if a.mode=='candidate' else None
        check('frozen criteria',r['criteria']['git_blob'],'413c9d8e9b2d3d9f6fa18829c7feacf53d23ea2e')
        check('producer passed',producer['passed'],True);check('producer preserved',producer['preserved'],True)
        check('producer source',producer['source_commit'],a.source);check('packet source',packet['commit'],a.source)
        check('packet identity bound',{k:producer['packet'][k] for k in ['bytes','sha256','git_blob']},r['packet'])
        check('criteria identity bound',{k:producer['criteria'][k] for k in ['bytes','sha256','git_blob']},r['criteria'])
        check('four ordinary CLI outcomes',[c['returncode'] for c in producer['children']],[0,0,2,2])
        expected={'criteria.json','producer.json','source-packet.json','receive_browser.py','mixed.html','empty.html','before.json','after.json','empty-before.json','empty-after.json'}
        if a.mode=='candidate':
            expected.add('baseline.json');check('baseline passed',baseline['passed'],True)
            check('baseline original source',baseline['source'],rules['original_commit']);check('same independent criteria',baseline['criteria'],r['criteria'])
        else:
            check('original source pin',a.source,rules['original_commit']);check('original packet pin',r['packet']['git_blob'],rules['original_packet'])
        check('complete admitted path set',sorted(r['before']),sorted(expected))
        check('executed observer admitted',ident(Path(__file__).read_bytes()),{k:r['before']['receive_browser.py'][k] for k in ['bytes','sha256','git_blob']})
        for name,pair in rules['cases'].items():
            check(name+' ordinary CLI HTML',{k:r['before'][name+'.html'][k] for k in ['bytes','sha256','git_blob']},{k:producer['pages'][name][k] for k in ['bytes','sha256','git_blob']})
            for f in pair:check('fixture '+f,{k:r['before'][f][k] for k in ['bytes','sha256','git_blob']},rules['fixtures'][f])
        pw=sync_playwright().start()
        browser=pw.chromium.launch(executable_path=a.chrome,headless=True,chromium_sandbox=True,downloads_path=str(downloads),env={**os.environ,'TEMP':str(temp),'TMP':str(temp)},args=['--no-first-run','--no-default-browser-check'])
        r['runtime']['browser_version']=browser.version
        context=browser.new_context(java_script_enabled=False,accept_downloads=True,viewport={'width':1280,'height':900})
        context.route('http://**/*',lambda route:route.abort());context.route('https://**/*',lambda route:route.abort())
        context.on('request',lambda request:r['requests'].append(request.url));page=context.new_page();page.set_default_timeout(10000)
        page.on('pageerror',lambda error:r['page_errors'].append(str(error)))
        for name,pair in rules['cases'].items():
            page.set_viewport_size({'width':1280,'height':900});page.goto((inp/(name+'.html')).as_uri(),wait_until='load')
            storage=page.evaluate(STORAGE);fixed=page.evaluate(FIXED);r['fixed'][name]=fixed
            files=rules['files'] if name=='mixed' else []
            check(name+' title',fixed['title'],'Compare saved TestPilot runs')
            check(name+' CSP',fixed['csp'],"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'")
            check(name+' no scripts',page.locator('script').count(),0)
            check(name+' file IDs',[x['id'] for x in fixed['files']],['file-'+str(x['index']) for x in files])
            table=[[x['path'],x['status'],str(len(x['before']['text'])) if 'text' in x['before'] else 'Absent',str(len(x['after']['text'])) if 'text' in x['after'] else 'Absent'] for x in files]
            check(name+' literal file table',fixed['fileTable'],table)
            check(name+' initial file disclosures',page.locator('#files details').evaluate_all('(xs)=>xs.map(x=>x.open)'),[x['status']!='unchanged' for x in files])
            originals=[]
            for role,fixture in zip(['before','after'],pair):
                b=(inp/fixture).read_bytes();originals.append({'id':'download-'+role,'label':'Download '+role+' JSON','name':role+'-report.json','href':'data:application/json;base64,'+base64.b64encode(b).decode()})
            check(name+' original JSON anchors',fixed['originals'],originals)
            expected_index=([{'href':'#diagnostic-before-case-1','text':'Before case 1 · failed · repeat <case> Ω'}, {'href':'#diagnostic-after-case-1','text':'After case 1 · error · repeat <case> Ω'}] if name=='mixed' else [])
            check(name+' retained diagnostic occurrence index',fixed['index'],expected_index)
            if a.mode=='candidate':check(name+' baseline complete fixed view',fixed,baseline['fixed'][name])
            # Open only the two originally collapsed unchanged-file disclosures in both epochs.
            for file in page.locator('#files details').all():
                if not file.evaluate('(x)=>x.open'):file.locator('summary').click()
            if name=='mixed':page.locator('#diagnostic-before-case-1 > summary').click()
            manual=page.locator('details').evaluate_all('(xs)=>xs.map(x=>({id:x.id,open:x.open}))')
            if a.mode=='original':
                check(name+' source actions absent',page.locator(rules['selectors']['link']).count(),0)
                check(name+' source unavailable notes absent',page.locator(rules['selectors']['unavailable']).count(),0)
            else:
                check(name+' source link count',page.locator(rules['selectors']['link']).count(),10 if name=='mixed' else 0)
                check(name+' unavailable count',page.locator(rules['selectors']['unavailable']).count(),2 if name=='mixed' else 0)
                for file in files:
                    for role in ['before','after']:
                        spec=file[role];label=f'file{file["index"]}-{role}'
                        attrs=f'[data-file-index="{file["index"]}"][data-role="{role}"]'
                        panel=page.locator('#file-'+str(file['index']))
                        link=panel.locator(rules['selectors']['link']+attrs);note=panel.locator(rules['selectors']['unavailable']+attrs)
                        if spec['state']=='download':
                            check(label+' visible label',link.text_content(),'Download '+role.title()+' source')
                            check(label+' unavailable note absent',note.count(),0)
                            meta,encoded=link.get_attribute('href').split(',',1)
                            check(label+' passive text URL',meta.lower() in ['data:text/plain;charset=utf-8;base64','data:text/plain;base64'],True)
                            expected_bytes=base64.b64decode(spec['base64'],validate=True)
                            check(label+' complete embedded bytes',base64.b64decode(encoded,validate=True)==expected_bytes,True)
                            keyboard=file['index']==6 and role=='after'
                            if keyboard:page.set_viewport_size({'width':390,'height':844})
                            save(page,link,spec['filename'],expected_bytes,label,keyboard)
                        else:
                            check(label+' no source link',link.count(),0)
                            if spec['state']=='absent':check(label+' no unavailable note',note.count(),0)
                            else:
                                check(label+' individual note',note.count(),1);text=note.text_content().lower()
                                check(label+' explicit surrogate reason',all(x in text for x in [role,'unavailable','unpaired','surrogate']),True)
                        check(label+' manual disclosure state',page.locator('details').evaluate_all('(xs)=>xs.map(x=>({id:x.id,open:x.open}))'),manual)
            for role,fixture in zip(['before','after'],pair):save(page,page.locator('#download-'+role),role+'-report.json',(inp/fixture).read_bytes(),name+'-'+role)
            page.set_viewport_size({'width':390,'height':844});check(name+'390 document fit',page.evaluate('document.documentElement.scrollWidth<=innerWidth'),True)
            page.locator('#file-1' if name=='mixed' else '#files').scroll_into_view_if_needed();page.screenshot(path=str(out/(name+'-390.png')))
            page.set_viewport_size({'width':1280,'height':900});page.locator('#files').scroll_into_view_if_needed();page.screenshot(path=str(out/(name+'-desktop.png')))
            # Collapse one native file then confirm print CSS exposes its source without mutating state.
            if name=='mixed':page.locator('#file-2 > summary').click()
            before_print=page.locator('details').evaluate_all('(xs)=>xs.map(x=>({id:x.id,open:x.open}))')
            page.emulate_media(media='print')
            visibility=page.locator('#files pre').evaluate_all('(xs)=>xs.map(x=>x.getBoundingClientRect().height>0)')
            check(name+' print complete source visibility',visibility,[True]*sum(len(x['pre']) for x in fixed['files']))
            page.emulate_media(media='screen')
            check(name+' print preserves disclosures',page.locator('details').evaluate_all('(xs)=>xs.map(x=>({id:x.id,open:x.open}))'),before_print)
            check(name+' complete fixed view after actions',page.evaluate(FIXED),fixed);check(name+' storage unchanged',page.evaluate(STORAGE),storage)
        check('actual saved download count',len(r['downloads']),4 if a.mode=='original' else 14)
        check('only two local page requests',r['requests'],[(inp/(n+'.html')).as_uri() for n in rules['cases']])
        check('no page errors',r['page_errors'],[]);check('context storage empty',context.storage_state(),{'cookies':[],'origins':[]});r['passed']=True
    except Exception as error:r.update(error=repr(error),traceback=traceback.format_exc())
    finally:
        if context:
            try:context.close();r['context_closed']=True
            except Exception as error:r['context_close_error']=repr(error);r['passed']=False
        if browser:
            try:browser.close();r['managed_disconnect']=not browser.is_connected();r['passed']=r['passed'] and r['managed_disconnect']
            except Exception as error:r['browser_close_error']=repr(error);r['passed']=False
        if pw:
            try:pw.stop();r['playwright_stopped']=True
            except Exception as error:r['playwright_stop_error']=repr(error);r['passed']=False
        r['after']=snap(inp);r['preserved']=r['before']==r['after'];r['passed']=r['passed'] and r['preserved']
        r['artifacts']={p.name:ident(p.read_bytes()) for p in sorted(out.iterdir()) if p.is_file()}
        r['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();(out/'receiving.json').write_text(json.dumps(r,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':r['passed'],'checks':len(r['checks']),'downloads':len(r['downloads']),'managed_disconnect':r['managed_disconnect'],'output':str(out)}))
    return 0 if r['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
