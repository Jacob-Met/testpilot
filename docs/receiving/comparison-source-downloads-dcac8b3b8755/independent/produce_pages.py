"""Run the ordinary offline comparison CLI on previously frozen fictional reports."""
from pathlib import Path, PurePosixPath
import argparse, datetime, hashlib, json, os, platform, subprocess, sys, traceback
sys.dont_write_bytecode = True

def identity(p):
    b = p.read_bytes(); s = p.stat()
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest(),
            'mode': s.st_mode, 'mtime_ns': str(s.st_mtime_ns), 'inode': str(s.st_ino)}

def snap(root):
    return {p.relative_to(root).as_posix(): identity(p) for p in sorted(root.rglob('*')) if p.is_file()}

def main():
    ap = argparse.ArgumentParser()
    for n in ['packet','criteria','fixtures','output']: ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--mode',choices=['original','candidate'],required=True)
    a=ap.parse_args(); a.output=a.output.resolve(); a.output.mkdir(exist_ok=False)
    source=a.output/'source'; source.mkdir()
    r={'schema':'hamon.testpilot130.independent-producer/1','mode':a.mode,
       'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'runtime':{'python':sys.version,'platform':platform.platform()},'checks':[],'children':[],'pages':{},'passed':False}
    watched=[a.packet.resolve(),a.criteria.resolve(),Path(__file__).resolve()]
    r['watched_before']={str(p):identity(p) for p in watched};r['fixtures_before']=snap(a.fixtures)
    def check(name,actual,expected):
        r['checks'].append({'name':name,'actual':actual,'expected':expected,'passed':actual==expected})
        if actual!=expected:raise RuntimeError(name)
    try:
        packet=json.loads(a.packet.read_bytes());criteria=json.loads(a.criteria.read_bytes())
        r.update(source_commit=packet['commit'],source_tree=packet['tree'],packet=identity(a.packet),criteria=identity(a.criteria))
        check('frozen criteria',r['criteria']['git_blob'],'413c9d8e9b2d3d9f6fa18829c7feacf53d23ea2e')
        check('packet schema',packet['schema'],'hamon.exact-text-source/1')
        check('packet repository',packet['repository'],'Jacob-Met/testpilot')
        if a.mode=='original':
            check('original source',packet['commit'],criteria['original_commit'])
            check('original exact packet',r['packet']['git_blob'],criteria['original_packet'])
        check('sixteen ordinary modules',len(packet['files']),16)
        seen=set()
        for f in packet['files']:
            rel=PurePosixPath(f['path'])
            if rel.is_absolute() or '..' in rel.parts or rel.parts[0]!='testpilot' or rel.suffix!='.py' or str(rel) in seen:raise ValueError('unexpected source path')
            seen.add(str(rel));p=source/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(f['content'].encode('utf-8'))
            check('source '+str(rel),identity(p)['git_blob'],f['git_blob'])
        r['source_before']=snap(source)
        for n,pin in criteria['fixtures'].items():check('fixture '+n,{k:r['fixtures_before'][n][k] for k in ['bytes','sha256','git_blob']},pin)
        for name,pair,code in [(n,p,0) for n,p in criteria['cases'].items()]+[(n,p,2) for n,p in criteria['negative_cases'].items()]:
            output=a.output/(name+'.html')
            cmd=[sys.executable,'-B','-m','testpilot','compare','--before',str((a.fixtures/pair[0]).resolve()),'--after',str((a.fixtures/pair[1]).resolve()),'--out',str(output)]
            child=subprocess.Popen(cmd,cwd=source,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:out,err=child.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                child.kill();out,err=child.communicate();raise RuntimeError('owned ordinary CLI timed out; killed and reaped')
            stdout=a.output/(name+'.stdout.txt');stderr=a.output/(name+'.stderr.txt');stdout.write_bytes(out);stderr.write_bytes(err)
            r['children'].append({'case':name,'argv':cmd,'cwd':str(source),'pid':child.pid,'returncode':child.returncode,'stdout':identity(stdout),'stderr':identity(stderr)})
            check(name+' exit',child.returncode,code)
            if code==0:
                check(name+' stderr',err.hex(),'')
                check(name+' delivered console line',out.decode('utf-8').splitlines(),['wrote '+str(output)])
                b=output.read_bytes();check(name+' complete UTF8 HTML',b.decode('utf-8').startswith('<!doctype html>') and b.decode('utf-8').endswith('</html>'),True)
                r['pages'][name]={'filename':output.name,'before':pair[0],'after':pair[1],**identity(output)}
            else:
                check(name+' no output publication',output.exists(),False)
                check(name+' no success console',out.hex(),'')
                check(name+' typed source refusal',b'expected text' in err,True)
        r['passed']=True
    except Exception as error:r.update(error=repr(error),traceback=traceback.format_exc())
    finally:
        r['source_after']=snap(source);r['fixtures_after']=snap(a.fixtures);r['watched_after']={str(p):identity(p) for p in watched}
        r['preserved']=r.get('source_before')==r['source_after'] and r['fixtures_before']==r['fixtures_after'] and r['watched_before']==r['watched_after']
        r['passed']=r['passed'] and r['preserved'];r['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        (a.output/'receiving.json').write_text(json.dumps(r,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':r['passed'],'checks':len(r['checks']),'children':len(r['children']),'preserved':r['preserved']}))
    return 0 if r['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
