"""Independent actual TestPilot module-CLI receiving, using disposable Git only.

python -B receive_targets.py --baseline ROOT --candidate ROOT --out results.json
No production files are modified. All child processes are local; preview children
trap model/runner/writer entry, network, and non-diff subprocess creation.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

SOURCE = {
    'baseline': '1f724ba942628f0b337f16594710bff11083ed33',
    'candidate': 'fc455a5b4866fd27503585a50903a80ff179513e',
}
SUPPORT = {
    'testpilot/__init__.py': '296210dd0d58703de4a4e4c9ad72a0944c9400ca',
    'testpilot/diff.py': 'd7d4c194c3730e4c7a8093b485491a7873afe814',
    'testpilot/loop.py': 'f4e9671b32cabda7e66ef79eb4a3a94c58d2f824',
    'testpilot/model.py': '20294ab3ad529b142ae955e1c4bc0ce71f87ae8b',
    'testpilot/sandbox.py': 'ca0360375bdcaace0e6014b4767acad546380242',
    'pyproject.toml': '952255ac87e2c7da57457fdbf3554914f17f6d05',
}
CONTRIBUTIONS = {
    'testpilot/__main__.py': SOURCE['candidate'],
    'tests/test_cli_targets.py': '281550909a8cce1067983199c5122e1bc5c0b78e',
    'docs/targets-preview.md': 'e8c89fa731ae13922057c5be5b03f0b35ce1b243',
}
SITE = r'''import atexit, json, os, subprocess, sys
from pathlib import Path
from types import SimpleNamespace
trace = {'ready': False, 'operations': [], 'forbidden': []}
trace_path = Path(os.environ['TP_RECEIVER_TRACE'])
mode = os.environ['TP_RECEIVER_MODE']
repo = os.environ['TP_RECEIVER_REPO']
atexit.register(lambda: trace_path.write_text(json.dumps(trace)))
def forbidden(name):
    def stop(*args, **kwargs):
        trace['forbidden'].append(name)
        raise RuntimeError('receiver refused '+name)
    return stop
allowed = ['git', '-C', repo, 'diff', 'HEAD', '--', '*.py']
def audit(event, args):
    if event in ('socket.connect', 'socket.getaddrinfo', 'os.system'):
        forbidden(event)()
    if event == 'subprocess.Popen' and (mode != 'preview' or list(args[1]) != allowed):
        forbidden('unexpected Popen')()
sys.addaudithook(audit)
real_run = subprocess.run
def checked_run(args, *pos, **kw):
    trace['operations'].append({'name':'subprocess.run', 'argv':list(args),
        'check':kw.get('check'), 'capture_output':kw.get('capture_output'), 'text':kw.get('text')})
    if mode != 'preview' or list(args) != allowed:
        forbidden('unexpected subprocess.run')()
    return real_run(args, *pos, **kw)
subprocess.run = checked_run
import testpilot.model as model
import testpilot.loop as loop
import testpilot.sandbox as sandbox
if mode == 'preview':
    model.make_client = forbidden('make_client')
    model.RoutingConfig.from_env = classmethod(forbidden('RoutingConfig.from_env'))
    loop.TestPilot = forbidden('TestPilot')
    loop.write_outputs = forbidden('write_outputs')
    loop.render_report = forbidden('render_report')
else:
    client, routing = object(), object()
    def make_client(backend, **kwargs):
        trace['operations'].append({'name':'make_client','backend':backend,'kwargs':kwargs})
        return client
    def from_env(cls):
        trace['operations'].append({'name':'RoutingConfig.from_env'})
        return routing
    class Pilot:
        def __init__(self, got_client, got_routing, **kwargs):
            trace['operations'].append({'name':'TestPilot','client_matches':got_client is client,
                'routing_matches':got_routing is routing,'kwargs':kwargs})
        def run(self, selected_repo, diff):
            trace['operations'].append({'name':'run','repo':selected_repo,'diff':diff})
            return SimpleNamespace(ok=True)
    def write_outputs(result, out):
        trace['operations'].append({'name':'write_outputs','ok':result.ok,'out':out})
        return {'report':Path(out)/'report.md','patch':Path(out)/'testpilot.patch'}
    def render_report(result):
        trace['operations'].append({'name':'render_report','ok':result.ok})
        return 'dispatch accepted\n## Patch\nnot printed'
    model.make_client = make_client
    model.RoutingConfig.from_env = classmethod(from_env)
    loop.TestPilot = Pilot
    loop.write_outputs = write_outputs
    loop.render_report = render_report
loop.run_pytest = forbidden('loop.run_pytest')
sandbox.run_pytest = forbidden('sandbox.run_pytest')
trace['ready'] = True
'''


def pin(path):
    raw = path.read_bytes()
    return {'git_blob': hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),
            'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def require(value, detail):
    if not value:
        raise RuntimeError(detail)


def verify_sources(roots):
    pins = {}
    for variant, root in roots.items():
        pins[variant] = {'testpilot/__main__.py': pin(root/'testpilot/__main__.py')}
        require(pins[variant]['testpilot/__main__.py']['git_blob'] == SOURCE[variant], 'wrong '+variant+' CLI')
        for rel, blob in SUPPORT.items():
            pins[variant][rel] = pin(root/rel)
            require(pins[variant][rel]['git_blob'] == blob, 'wrong support '+variant+' '+rel)
    for rel, blob in CONTRIBUTIONS.items():
        actual = pin(roots['candidate']/rel)
        require(actual['git_blob'] == blob, 'wrong contribution '+rel)
        pins['candidate'][rel] = actual
    before = (roots['baseline']/'testpilot/__main__.py').read_text()
    after = (roots['candidate']/'testpilot/__main__.py').read_text()
    marker = '    if a.diff == "-":\n'
    require(before[before.index(marker):] == after[after.index(marker):], 'run tail changed')
    old_ast, new_ast = ast.parse(before), ast.parse(after)
    def function(tree, name):
        return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    require(ast.get_source_segment(before, function(old_ast,'_python_executable')) ==
            ast.get_source_segment(after, function(new_ast,'_python_executable')), 'interpreter helper changed')
    old_stmts, new_stmts = function(old_ast,'main').body, function(new_ast,'main').body
    def assignment(node, name):
        return isinstance(node, ast.Assign) and any(isinstance(t,ast.Name) and t.id == name for t in node.targets)
    old_parser = old_stmts[:next(i for i,n in enumerate(old_stmts) if assignment(n,'a'))]
    new_parser = new_stmts[:next(i for i,n in enumerate(new_stmts) if assignment(n,'preview'))]
    require([ast.dump(n) for n in old_parser] == [ast.dump(n) for n in new_parser], 'run parser changed')
    return {'pins':pins,'run_tail_byte_identical':True,'run_parser_AST_identical':True,
            'interpreter_helper_byte_identical':True,'all_six_support_files_exact':True}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--baseline',type=Path,required=True)
    ap.add_argument('--candidate',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    roots={k:getattr(args,k).resolve() for k in ('baseline','candidate')}
    preservation=verify_sources(roots)
    records=[]
    with tempfile.TemporaryDirectory(prefix='tp-native-receiver-',dir=args.out.resolve().parent) as temp:
        root=Path(temp); repo=root/'project'; repo.mkdir()
        hook=root/'hooks'; hook.mkdir(); (hook/'sitecustomize.py').write_text(SITE)
        global_config=root/'empty-gitconfig'; global_config.write_text('')
        common={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'PYTHONIOENCODING':'utf-8',
                'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1',
                'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':str(global_config),
                'GIT_TERMINAL_PROMPT':'0','GIT_OPTIONAL_LOCKS':'0'}
        def git(*argv):
            p=subprocess.run(['git','-C',str(repo),*argv],env=common,capture_output=True,text=True)
            require(p.returncode==0,'disposable Git failed: '+p.stderr)
            return p.stdout
        odd='src/odd\n\u540d\u5b57.py'
        original={
            odd:'from pathlib import Path\nPath(__file__).with_name("project-imported").write_text("bad")\nraise RuntimeError("do not import selected source")\n\ndef outer(value):\n    def normalize(v):\n        return v + 10\n    dropped = 9\n    return normalize(value)\n',
            'lib/conditional.py':'if True:\n    class Adapter:\n        @staticmethod\n        async def format_value(value):\n            return str(value)\n\ndef untouched():\n    return 3\n',
            'src/config.py':'VALUE = 1\n',
            'tests/test_noise.py':'def test_noise():\n    assert 1\n',
            'conftest.py':'raise RuntimeError("pytest must not start")\n',
            'docs/design.txt':'old text\n',
            'deleted.py':'def deleted():\n    return 8\n',
            'zz_invalid.py':'def broken(value):\n    return value\n',
        }
        for rel,text in original.items():
            p=repo/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
        git('init','-q');git('add','--all')
        git('-c','user.name=Disposable Receiver','-c','user.email=receiver@example.invalid','-c','core.hooksPath='+str(root/'no-hooks'),'commit','-qm','fixture')
        (repo/odd).write_text(original[odd].replace('    dropped = 9\n',''))
        (repo/'lib/conditional.py').write_text(original['lib/conditional.py'].replace('return str(value)','return f"<{value}>"'))
        (repo/'src/config.py').write_text('VALUE = 2\n')
        (repo/'tests/test_noise.py').write_text('def test_noise():\n    assert 2\n')
        (repo/'docs/design.txt').write_text('new text\n')
        (repo/'deleted.py').unlink()
        diff=git('diff','HEAD','--','*.py')
        saved=root/'selected.diff';saved.write_text(diff)
        spec=importlib.util.spec_from_file_location('receiving_native_diff',roots['baseline']/'testpilot/diff.py')
        native=importlib.util.module_from_spec(spec);sys.modules[spec.name]=native;spec.loader.exec_module(native)
        expected=[f.to_dict() for f in native.changed_functions(repo,diff)]
        require(len(expected)==2,'fixture must select two eligible functions')
        by_name={f['qualname']:f for f in expected}
        require(set(by_name)=={'outer','Adapter.format_value'},'unexpected native identities')
        require(by_name['outer']['path']==odd and by_name['outer']['changed_lines']==[] and
                (by_name['outer']['lineno'],by_name['outer']['end_lineno'])==(5,8),'pure deletion attribution')
        require(by_name['Adapter.format_value']['is_method'] and
                (by_name['Adapter.format_value']['lineno'],by_name['Adapter.format_value']['end_lineno'])==(3,5) and
                by_name['Adapter.format_value']['changed_lines']==[5],'decorated async conditional method attribution')
        human='2 changed Python functions outside tests\n'+''.join(
            f'{json.dumps(f["path"])}:{f["lineno"]}-{f["end_lineno"]}  {json.dumps(f["qualname"])}\n' for f in expected)
        def snapshot():
            return {p.relative_to(repo).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in repo.rglob('*') if p.is_file() and '.git' not in p.relative_to(repo).parts}
        def invoke(variant,label,argv,stdin='',mode='preview'):
            trace=root/(variant+'-'+label+'.json')
            env=dict(common,PYTHONPATH=os.pathsep.join((str(hook),str(roots[variant]))),
                     TP_RECEIVER_TRACE=str(trace),TP_RECEIVER_MODE=mode,TP_RECEIVER_REPO=str(repo))
            before=snapshot()
            command=[sys.executable,'-B','-m','testpilot',*argv]
            done=subprocess.run(command,cwd=root,env=env,input=stdin,capture_output=True,text=True,timeout=20)
            receipt=json.loads(trace.read_text()) if trace.exists() else {'ready':False,'forbidden':['missing trace'],'operations':[]}
            return {'variant':variant,'case':label,'child_exit':done.returncode,'stdout':done.stdout,
                    'stderr':done.stderr,'trace':receipt,'project_bytes_unchanged':snapshot()==before}
        for label,extra,stdin,is_json,git_expected in [
            ('native-git-json',['--git-base','HEAD','--json'],'',True,True),
            ('saved-human',['--diff',str(saved)],'',False,False),
            ('stdin-json',['--diff','-','--json'],diff,True,False),
        ]:
            for variant in roots:
                r=invoke(variant,label,['targets','--repo',str(repo),*extra],stdin)
                try: actual=json.loads(r['stdout'])
                except ValueError: actual=None
                operations=r['trace']['operations']
                r['checks']={'exit_zero':r['child_exit']==0,'empty_stderr':r['stderr']=='',
                    'native_records_or_exact_human':actual=={'changed_functions':expected} if is_json else r['stdout']==human,
                    'trace_ready':r['trace']['ready'],'no_model_runner_writer_or_network':r['trace']['forbidden']==[],
                    'only_expected_git_diff':operations==[{'name':'subprocess.run','argv':['git','-C',str(repo),'diff','HEAD','--','*.py'],
                         'check':True,'capture_output':True,'text':True}] if git_expected else operations==[],
                    'project_bytes_unchanged':r['project_bytes_unchanged']}
                records.append(r)
        # An invalid final source comes after both valid records in the diff;
        # the preview must not emit either a partial table or partial JSON.
        (repo/'zz_invalid.py').write_text('def broken(:\n    return 1\n')
        invalid=git('diff','HEAD','--','*.py')
        require(invalid.rfind('zz_invalid.py')>invalid.find('lib/conditional.py'),'error fixture order')
        for variant in roots:
            r=invoke(variant,'no-partial-preview',['targets','--repo',str(repo),'--diff','-','--json'],invalid)
            r['checks']={'exit_two':r['child_exit']==2,'stdout_empty':r['stdout']=='',
                'native_error_reported':'testpilot: cannot inspect targets:' in r['stderr'] and 'zz_invalid.py' in r['stderr'] and 'Traceback' not in r['stderr'],
                'trace_ready':r['trace']['ready'],'no_effects':r['trace']['forbidden']==[] and r['trace']['operations']==[],
                'project_bytes_unchanged':r['project_bytes_unchanged']}
            records.append(r)
        interpreter=root/'venv-bin'/'python';interpreter.parent.mkdir();interpreter.symlink_to(sys.executable)
        run_out=root/'never-written';scripts=root/'scripted-input';scripts.mkdir()
        command=['run','--repo',str(repo),'--diff','-','--backend','scripted','--script',str(scripts),
                 '--base-url','https://receiver.invalid/v1','--rounds','7','--timeout','1.25','--max-tokens','314',
                 '--python',str(interpreter),'--out',str(run_out)]
        run_pair={}
        for variant in roots:
            r=invoke(variant,'preserved-run-dispatch',command,diff,mode='dispatch')
            ops=r['trace']['operations'];names=[o['name'] for o in ops]
            init=next((o for o in ops if o['name']=='TestPilot'),{})
            native_run=next((o for o in ops if o['name']=='run'),{})
            r['checks']={'exit_zero':r['child_exit']==0,'empty_stderr':r['stderr']=='',
                'ordered_run_dispatch':names==['make_client','RoutingConfig.from_env','TestPilot','run','write_outputs','render_report'],
                'all_run_options_preserved':init.get('kwargs')=={'max_repair_rounds':7,'timeout_s':1.25,'max_total_tokens':314,'python':str(interpreter)} and init.get('client_matches') and init.get('routing_matches'),
                'original_diff_and_repo':native_run.get('diff')==diff and native_run.get('repo')==str(repo),
                'trace_ready_no_real_effects':r['trace']['ready'] and r['trace']['forbidden']==[] and not run_out.exists(),
                'project_bytes_unchanged':r['project_bytes_unchanged']}
            run_pair[variant]=r;records.append(r)
        dispatch_parity=all(run_pair['baseline'][k]==run_pair['candidate'][k] for k in ('child_exit','stdout','stderr','trace'))
        require(dispatch_parity,'baseline/candidate run dispatch differs')
        report={'source_preservation':preservation,'native_expected':expected,'exact_human_expected':human,
                'records':records,'run_dispatch_exact_pair':dispatch_parity,
                'actual_Python_CLI_children':len(records),'native_Git_diff_inside_CLI_children':sum(any(o['name']=='subprocess.run' for o in r['trace']['operations']) for r in records),
                'candidate_conditions':sum(len(r['checks']) for r in records if r['variant']=='candidate'),
                'candidate_failed_conditions':sum(not bool(v) for r in records if r['variant']=='candidate' for v in r['checks'].values()),
                'baseline_failed_conditions':sum(not bool(v) for r in records if r['variant']=='baseline' for v in r['checks'].values()),
                'receiver':pin(Path(__file__)),'python':sys.version,
                'limits':['Actual local module CLI and Git; no project import, model/provider, pytest, report output, live account or service.',
                          'Existing run dispatch is controlled at factory/runner/writer boundaries; author native run control is separate.',
                          'Preview retains native Git configuration policy; fixture Git configuration is explicit and disposable.',
                          'No native Windows qualification or full repository test suite.']}
        args.out.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:report[k] for k in ('actual_Python_CLI_children','native_Git_diff_inside_CLI_children','candidate_conditions','candidate_failed_conditions','baseline_failed_conditions','run_dispatch_exact_pair')}))
        return int(bool(report['candidate_failed_conditions']))


if __name__=='__main__':
    raise SystemExit(main())
