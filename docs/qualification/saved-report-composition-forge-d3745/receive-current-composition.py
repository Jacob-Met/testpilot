"""Source-aware current-main composition receiving; no browser or model operation."""
import base64,hashlib,json,os,pathlib,platform,signal,subprocess,sys,time,datetime
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/'evidence'
def ident(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':p.stat().st_mode&0o777}
admission=json.loads((ROOT/'source-admission.json').read_bytes())
sources=[pathlib.Path(r['path']) for r in admission['files']]
controls=[ROOT/'input-packet.json',ROOT/'receiving-contract.json',ROOT/'stage-source.py',ROOT/'source-admission.json',pathlib.Path(__file__)]
before=[ident(p) for p in sources+controls]
for r,a in zip(admission['files'],before):
 assert all(r[k]==a[k] for k in ['path','bytes','sha256','mode'])
report={'schema':'hamon.forge.testpilot-saved-review-composition-receiving.v1','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':os.getpid(),'python':sys.version,'platform':platform.platform(),'source_admission':ident(ROOT/'source-admission.json'),'criteria':json.loads((ROOT/'receiving-contract.json').read_bytes()),'inputs_before':before,'commands':[],'checks':[],'accepted':False}
env=os.environ.copy()
for k in ['PYTHONPATH','PYTHONHOME','PYTHONPYCACHEPREFIX']:env.pop(k,None)
env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',TMPDIR=str(ROOT/'tmp'))
def check(label,actual,expected=True):
 ok=actual==expected;report['checks'].append({'label':label,'actual':actual,'expected':expected,'pass':ok})
 if not ok:raise AssertionError(label)
def run(label,argv,cwd):
 p=subprocess.Popen(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 row={'label':label,'argv':argv,'cwd':str(cwd),'pid':p.pid,'timeout_s':90};report['commands'].append(row)
 try:out,err=p.communicate(timeout=90)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate();row['timeout']=True
 row['returncode']=p.returncode
 for name,b in [('stdout',out),('stderr',err)]:
  f=OUT/(label+'.'+name);f.write_bytes(b);row[name]=ident(f);row[name+'_text']=b.decode('utf-8',errors='backslashreplace')
 return p.returncode,out,err
class Page(HTMLParser):
 def __init__(self,text):super().__init__();self.downloads={};self.tags=[];self.feed(text)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);self.tags.append(tag)
  if tag=='a' and 'download' in a:self.downloads[a['download']]=base64.b64decode(a['href'].split(',',1)[1],validate=True)
try:
 original=ROOT/'baseline';combined=ROOT/'combined'
 def command(report_path,patch_path,destination):
  return [sys.executable,'-B','-S','-m','testpilot.saved_report','--report',str(report_path),'--patch',str(patch_path),'--out',str(destination)]
 source_report=original/'eval/results/calc_clamp/report.json';source_patch=original/'eval/results/calc_clamp/testpilot.patch'
 code,out,err=run('01-current-absent',command(source_report,source_patch,OUT/'baseline-absent.html'),original)
 check('current main module absent exit',code,1);check('current absence diagnostic',b'No module named testpilot.saved_report' in err)
 check('current absence has no stdout',out,b'');check('current absence creates no output',not(OUT/'baseline-absent.html').exists())
 code,out,err=run('02-maintained-eight',[sys.executable,'-B','-S','-m','unittest','discover','-v','-s','tests','-p','test_saved_report.py'],combined)
 check('donor maintained methods exit',code,0);check('all eight donor methods ran',b'Ran 8 tests' in err);check('donor maintained result OK',err.rstrip().endswith(b'OK'))
 consumer=ROOT/'consumer';consumer.mkdir()
 rp=consumer/'report.json';pp=consumer/'selected.patch';target=consumer/'review.html'
 rp.write_bytes(source_report.read_bytes());pp.write_bytes((original/'eval/results/stats_median/testpilot.patch').read_bytes())
 report['mismatched_inputs']=[ident(rp),ident(pp)]
 args=command(rp,pp,target)
 code,out,err=run('03-pair-refusal',args,combined)
 check('mismatched pair exit',code,2);check('mismatched pair diagnostic',b'do not match' in err)
 check('mismatched pair no stdout',out,b'');check('mismatched pair creates no output',not target.exists())
 check('mismatched pair no staging files',list(consumer.glob('.testpilot-review-*')),[])
 check('refusal retains report',rp.read_bytes(),source_report.read_bytes())
 check('refusal retains wrong selected patch',pp.read_bytes(),(original/'eval/results/stats_median/testpilot.patch').read_bytes())
 pp.write_bytes(source_patch.read_bytes());report['explicit_corrected_inputs']=[ident(rp),ident(pp)]
 code,out,err=run('04-caller-corrected-retry',args,combined)
 check('identical argv on explicit retry',report['commands'][-1]['argv'],report['commands'][-2]['argv'])
 check('corrected pair exit',code,0);check('corrected pair empty stderr',err,b'')
 receipt=json.loads(out);page_bytes=target.read_bytes();page=Page(page_bytes.decode())
 check('saved output digest',receipt['sha256'],hashlib.sha256(page_bytes).hexdigest())
 check('saved output length',receipt['bytes'],len(page_bytes))
 check('exact original report download',page.downloads['report.json'],source_report.read_bytes())
 check('exact original patch download',page.downloads['testpilot.patch'],source_patch.read_bytes())
 check('only original artifact downloads',sorted(page.downloads),['report.json','testpilot.patch'])
 check('historical status preserved',receipt['recorded_status'],json.loads(source_report.read_bytes())['status'])
 check('passive tags only',not(set(page.tags)&{'script','iframe','object','img'}))
 check('historical provenance notice',b'No tests or model requests ran.' in page_bytes)
 check('successful publish leaves no staging files',list(consumer.glob('.testpilot-review-*')),[])
 report['received_page']=ident(target);report['receipt']=receipt
 code,out,err=run('05-occupied-output',args,combined)
 check('occupied output refusal exit',code,2);check('occupied output diagnostic',b'output already exists' in err)
 check('occupied output no stdout',out,b'');check('prior successful page preserved',target.read_bytes(),page_bytes)
 check('final selected report preserved',rp.read_bytes(),source_report.read_bytes())
 check('final corrected patch preserved',pp.read_bytes(),source_patch.read_bytes())
 report['accepted']=True
except BaseException as exc:
 report['error']={'type':type(exc).__name__,'message':str(exc)}
finally:
 report['inputs_after']=[ident(p) for p in sources+controls]
 if report['inputs_after']!=before:report['accepted']=False;report['custody_error']='Source/control changed'
 report['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 # Comparison records carry digests for bytes rather than JSON-encoding raw bytes.
 def clean(value):
  if isinstance(value,bytes):return {'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()}
  if isinstance(value,pathlib.Path):return str(value)
  if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
  if isinstance(value,list):return [clean(v) for v in value]
  return value
 report=clean(report);p=OUT/'composition-receipt.json'
 with p.open('x',encoding='utf-8') as f:json.dump(report,f,sort_keys=True,indent=2);f.write(chr(10))
 print(json.dumps({'accepted':report['accepted'],'checks':len(report['checks']),'commands':len(report['commands']),'receipt':ident(p)}))
sys.exit(0 if report['accepted'] else 1)
