"""Receive the new preview interface over the already-merged native BOM reader.

python -B receive_bom_preview.py --candidate ROOT --receiver receive_targets_current.py --out results.json
The independent receiver's unchanged child tripwires are reused, not its suite.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


def pin(path):
    raw=path.read_bytes()
    return {'git_blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),
            'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--candidate',required=True,type=Path)
    ap.add_argument('--receiver',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    args=ap.parse_args();source=args.candidate.resolve()
    if pin(source/'testpilot/__main__.py')['git_blob']!='fc455a5b4866fd27503585a50903a80ff179513e':
        raise RuntimeError('Unexpected preview source')
    if pin(source/'testpilot/diff.py')['git_blob']!='d7d4c194c3730e4c7a8093b485491a7873afe814':
        raise RuntimeError('Unexpected merged decoder')
    support=load('targets_current_receiver',args.receiver)
    native=load('bom_current_native_diff',source/'testpilot/diff.py')
    with tempfile.TemporaryDirectory(prefix='tp-bom-preview-',dir=args.out.resolve().parent) as temp:
        root=Path(temp);repo=root/'repo';repo.mkdir();(repo/'src').mkdir()
        hooks=root/'hooks';hooks.mkdir();(hooks/'sitecustomize.py').write_text(support.SITE)
        config=root/'gitconfig';config.write_text('')
        env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'PYTHONIOENCODING':'utf-8',
             'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','GIT_CONFIG_NOSYSTEM':'1',
             'GIT_CONFIG_GLOBAL':str(config),'GIT_TERMINAL_PROMPT':'0','GIT_OPTIONAL_LOCKS':'0'}
        def git(*args):
            r=subprocess.run(['git','-C',str(repo),*args],env=env,capture_output=True,text=True)
            if r.returncode:raise RuntimeError(r.stderr)
            return r.stdout
        original=b'\xef\xbb\xbf# Native BOM source\nfrom pathlib import Path\nPath(__file__).with_name("imported").write_text("bad")\nraise RuntimeError("must not import")\ndef emit():\n    return "old"\n'
        path=repo/'src/encoded.py';path.write_bytes(original)
        git('init','-q');git('add','--all')
        git('-c','user.name=Disposable Receiver','-c','user.email=receiver@example.invalid','-c','core.hooksPath='+str(root/'none'),'commit','-qm','BOM fixture')
        changed=original.replace(b'"old"',b'"new"');path.write_bytes(changed)
        diff=git('diff','HEAD','--','*.py')
        expected=[f.to_dict() for f in native.changed_functions(repo,diff)]
        if len(expected)!=1 or expected[0]['qualname']!='emit' or expected[0]['source']!='def emit():\n    return "new"':
            raise RuntimeError('BOM native fixture selection differs')
        trace=root/'trace.json'
        child_env=dict(env,PYTHONPATH=os.pathsep.join((str(hooks),str(source))),
                       TP_RECEIVER_TRACE=str(trace),TP_RECEIVER_MODE='preview',TP_RECEIVER_REPO=str(repo))
        child=subprocess.run([sys.executable,'-B','-m','testpilot','targets','--repo',str(repo),'--git-base','HEAD','--json'],
                             cwd=root,env=child_env,capture_output=True,text=True,timeout=20)
        observed=json.loads(trace.read_text())
        try:actual=json.loads(child.stdout)
        except ValueError:actual=None
        checks={'exit_zero':child.returncode==0,'empty_stderr':child.stderr=='',
                'native_BOM_record_received':actual=={'changed_functions':expected},
                'source_BOM_bytes_preserved':path.read_bytes()==changed,
                'no_project_import':not (repo/'src/imported').exists(),
                'no_generation_tests_writers_or_network':observed['ready'] and observed['forbidden']==[],
                'one_native_Git_diff':observed['operations']==[{'name':'subprocess.run','argv':['git','-C',str(repo),'diff','HEAD','--','*.py'],
                    'check':True,'capture_output':True,'text':True}]}
        result={'checks':checks,'failures':sum(not value for value in checks.values()),'actual_Python_CLI_children':1,
                'source':{p:pin(source/p) for p in ['testpilot/__main__.py','testpilot/diff.py']},
                'child_exit':child.returncode,'stdout':child.stdout,'stderr':child.stderr,'trace':observed,
                'native_expected':expected,'diff':diff,'receiver':pin(Path(__file__)),
                'attribution':'The Python encoding reader belongs to merged PR #15. This receives only the new preview interface over that unchanged native reader.',
                'limits':'Disposable local Git/Python only, no project import/model/pytest/provider/service. No owner encoding-suite rerun.'}
        args.out.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'conditions':len(checks),'failures':result['failures'],'actual_Python_CLI_children':1}))
        return int(bool(result['failures']))


if __name__=='__main__':
    raise SystemExit(main())
