"""Actual TestPilot retained regression on exact CaptureSuite Python snapshots.

Local fixture commits are explicitly distinct from original source commits.
The source packages are unmodified, with an added receiving configuration.
"""
import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

BASE_PIN='3960c0c756cd4e9facbde0d76eaaa3c31ab7c167'
FIX_PIN='95ae1955dcff15c7cc4df77ebe66817dbc9b8094'
TOOLKIT_PIN='a5c292bc9f9f3e05b88bb3feee94cfb7159e4a15'
EMG='libs/python/capture_analysis/capture_analysis/features/emg.py'
FIX_SHA='f1b0bd94e397bfc5a60df62c4679b50b2e8a683d9c9177f76f74d59ff11dad6a'
TEST='''import numpy as np
from capture_analysis.features.emg import extract_emg_features
from capture_analysis.types import GapInterval, GapMask, LoadedEmg, StreamRef, TimeWindow

def measured(gaps):
    times=np.array([0,25_000_000,125_000_000,150_000_000],dtype=np.int64)
    samples=np.array([[1,1,-1,-1]],dtype=np.float32)
    stream=StreamRef('retained.emg','samples','emg','emg.batch/1',40.0,'mV')
    mask=GapMask(stream,TimeWindow(0,150_000_000),gaps,'mask')
    table,_,fraction=extract_emg_features(LoadedEmg(['ch0'],times,samples,40.0,'mV'),mask,window_s=.1,hop_s=.1)
    np.testing.assert_array_equal(samples,[[1,1,-1,-1]])
    np.testing.assert_array_equal(times,[0,25_000_000,125_000_000,150_000_000])
    row=table.iloc[0]
    assert (row.ch0_rms,row.ch0_mav,row.valid_fraction,fraction)==(1,1,1,1)
    assert row.t_mid_ns==75_000_000
    return row

def test_no_recorded_gap_retains_observed_transition():
    row=measured([])
    assert (row.ch0_wl,row.ch0_zc,row.ch0_ssc)==(2,1,0)

def test_recorded_disconnect_does_not_invent_transition():
    gap=GapInterval('retained.emg','samples','DISCONNECT',50_000_000,100_000_000,True)
    row=measured([gap])
    assert (row.ch0_wl,row.ch0_zc,row.ch0_ssc)==(0,0,0)
'''

def sha(data):return hashlib.sha256(data).hexdigest()

def collect_existing(a):
    out=a.out.resolve();project=out/'source-snapshots'
    generated=json.loads((out/'generated/report.json').read_text())
    regression=json.loads((out/'regression/regression.json').read_text())
    provenance=json.loads((project/'SOURCE_PROVENANCE.json').read_text())
    assert generated['ok'] and generated['final']['passed']==3 and generated['final']['generated']['passed']==2
    assert generated['test_files']=={'tests/test_emg_retained.py':TEST}
    assert regression['status']=='verified_regression' and regression['model_calls']==0
    assert len(regression['comparison']['witnesses'])==1
    assert regression['source_report']['sha256']==sha((out/'generated/report.json').read_bytes())
    counts={}
    for label,root,total,retained,failed in [('before',a.baseline,2,1,1),('after',a.corrected,3,2,0)]:
        result=regression[label]['result']
        assert result['passed']==total and result['failed']==failed and result['errors']==0
        assert result['generated']['passed']==retained and result['generated']['failed']==failed
        assert {n:sha((root/n).read_bytes()) for n in provenance['source_files'][label]}==provenance['source_files'][label]
        counts[label]={'total_passed':total,'total_failed':failed,'retained_passed':retained,'retained_failed':failed}
    assert {n:sha((project/n).read_bytes()) for n in provenance['source_files']['after']}==provenance['source_files']['after']
    assert not (project/'tests/test_emg_retained.py').exists()
    r=subprocess.run(['git','-C',str(project),'status','--porcelain'],capture_output=True,text=True,timeout=10)
    assert r.returncode==0 and r.stdout==''
    receipt={'status':'ACCEPT','observed_at_utc':datetime.now(timezone.utc).isoformat(),'source_provenance':provenance,
             'local_fixture_commits':{side:regression[side]['commit'] for side in ['before','after']},
             'native_counts':counts,'generated_native_cases':3,'retained_generated_cases':2,
             'regression_status':regression['status'],'witnesses':regression['comparison']['witnesses'],
             'regression_model_calls':0,'source_and_worktree_preserved':True,'collected_existing_results_without_rerun':True,
             'receiver_setup_note':'The initial post-run assertion incorrectly treated total native cases as retained-only cases. Both completed CLI outputs already passed their substantive checks; collection now distinguishes the unchanged smoke test and retained tests.',
             'limits':['Synthetic in-memory EMG inputs exercising exact public source, not MCAP/hardware.','Local fixture commits represent exact Python subsets, not full CaptureSuite histories.','Fixed-response generation; no live model quality or installed deployment claim.']}
    (out/'receiving.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='source_provenance'},indent=2))

def main():
    ap=argparse.ArgumentParser()
    for n in ['baseline','corrected','testpilot-source','project-python','license','out']:ap.add_argument('--'+n,required=True,type=Path)
    ap.add_argument('--collect-existing',action='store_true',help='verify and collect already completed native CLI outputs without rerunning')
    a=ap.parse_args()
    if a.collect_existing:return collect_existing(a)
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    project=out/'source-snapshots';project.mkdir();tmp=out/'native-tmp';tmp.mkdir()
    roots={'before':a.baseline,'after':a.corrected}
    sources={label:{str(p.relative_to(root)):p.read_bytes() for p in (root/'libs/python').rglob('*.py') if '__pycache__' not in p.parts} for label,root in roots.items()}
    originals={label:{n:sha(b) for n,b in source.items()} for label,source in sources.items()}
    assert sources['before'].keys()==sources['after'].keys()
    assert [n for n in sources['before'] if sources['before'][n]!=sources['after'][n]]==[EMG]
    assert sha(sources['after'][EMG])==FIX_SHA
    provenance={'before_source_commit':BASE_PIN,'after_source_commit':FIX_PIN,'toolkit_source_commit':TOOLKIT_PIN,'source_files':originals,
                'scope':'Exact Python package subset, receiving pytest configuration, unchanged native smoke test. Local fixture commits differ from original repository commits.'}
    (project/'SOURCE_PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n');shutil.copyfile(a.license,project/'LICENSE')
    (project/'pytest.ini').write_text('[pytest]\npythonpath = libs/python/capture_analysis libs/python/capture_session libs/python/capture_protocol\n')
    (project/'tests').mkdir();(project/'tests/test_native_smoke.py').write_text('from capture_analysis.types import TimeWindow\ndef test_native_smoke():\n    assert TimeWindow(0,1).contains(1)\n')
    env={k:v for k,v in os.environ.items() if not k.startswith('TESTPILOT_') and not k.startswith('GIT_')}
    env.update(PYTHONPATH=str(a.testpilot_source.resolve()),PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(tmp),GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_TERMINAL_PROMPT='0')
    def git(*args):
        r=subprocess.run(['git','-C',str(project),*args],env=env,capture_output=True,text=True,timeout=20)
        assert r.returncode==0,(args,r.stderr);return r.stdout.strip()
    git('init','-q');commits=[]
    for label in ('before','after'):
        for n,b in sources[label].items():
            p=project/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        git('add','.');git('-c','user.name=HAMON receiving fixture','-c','user.email=fixture@example.invalid','commit','--no-gpg-sign','-qm',label+' exact Python source snapshot')
        commits.append(git('rev-parse','HEAD'))
    diff=out/'emg-change.diff';diff.write_text(''.join(difflib.unified_diff(sources['before'][EMG].decode().splitlines(True),sources['after'][EMG].decode().splitlines(True),fromfile='a/'+EMG,tofile='b/'+EMG)))
    scripts=out/'responses';scripts.mkdir();(scripts/'01.txt').write_text('Retain a no-gap control and one recorded-disconnect witness. Preserve source inputs and amplitude/time semantics.')
    (scripts/'02.txt').write_text('```python path=tests/test_emg_retained.py\n'+TEST+'```\n')
    commands=[]
    def run(label,args):
        command=[sys.executable,'-B','-m','testpilot',*args]
        with (out/(label+'.stdout')).open('wb') as stdout,(out/(label+'.stderr')).open('wb') as stderr:r=subprocess.run(command,cwd=out,env=env,stdout=stdout,stderr=stderr,stdin=subprocess.DEVNULL,timeout=90)
        commands.append({'label':label,'command':command,'returncode':r.returncode})
        assert r.returncode==0,(label,r.returncode,(out/(label+'.stderr')).read_text()[-3000:])
    report=out/'generated'
    run('generate-retained-tests',['run','--repo',str(project),'--diff',str(diff),'--backend','scripted','--script',str(scripts),'--rounds','0','--timeout','30','--no-coverage','--progress','--python',str(a.project_python.absolute()),'--target',EMG+'::extract_emg_features','--out',str(report)])
    generated=json.loads((report/'report.json').read_text())
    assert generated['ok'] and generated['final']['passed']==3 and generated['final']['generated']['passed']==2
    assert generated['test_files']=={'tests/test_emg_retained.py':TEST}
    assert not (project/'tests/test_emg_retained.py').exists()
    resultdir=out/'regression'
    run('actual-retained-regression',['regression','--repo',str(project),'--report',str(report/'report.json'),'--before',commits[0],'--after',commits[1],'--timeout','30','--python',str(a.project_python.absolute()),'--out',str(resultdir)])
    regression=json.loads((resultdir/'regression.json').read_text())
    assert regression['status']=='verified_regression' and regression['model_calls']==0 and len(regression['comparison']['witnesses'])==1
    assert regression['before']['result']['passed']==2 and regression['before']['result']['failed']==1
    assert regression['after']['result']['passed']==3 and regression['after']['result']['failed']==0
    assert git('status','--porcelain')==''
    for label,root in roots.items():assert {n:sha((root/n).read_bytes()) for n in originals[label]}==originals[label]
    receipt={'status':'ACCEPT','observed_at_utc':datetime.now(timezone.utc).isoformat(),'source_provenance':provenance,'local_fixture_commits':dict(zip(['before','after'],commits)),
             'generated_native_cases':3,'retained_generated_cases':2,'regression_status':regression['status'],'before_cases':{'passed':2,'failed':1},'after_cases':{'passed':3,'failed':0},
             'witnesses':regression['comparison']['witnesses'],'regression_model_calls':0,'source_and_worktree_preserved':True,'commands':commands,
             'limits':['Synthetic in-memory EMG inputs exercising exact public source, not MCAP/hardware.','Local fixture commits represent exact Python subsets, not full CaptureSuite histories.','Fixed-response generation; no live model quality or installed deployment claim.']}
    (out/'receiving.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ('source_provenance','commands')},indent=2))

if __name__=='__main__':main()
