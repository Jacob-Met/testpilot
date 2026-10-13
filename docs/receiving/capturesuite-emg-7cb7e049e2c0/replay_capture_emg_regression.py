"""Replay the saved EMG regression using the received TestPilot toolkit."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--packet',type=Path,default=Path(__file__).resolve().parent)
    ap.add_argument('--toolkit',type=Path,required=True)
    ap.add_argument('--python',type=Path,required=True,help='Python with CaptureSuite analysis dependencies and pytest')
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();packet=a.packet.resolve();toolkit=a.toolkit.resolve();out=a.out.resolve()
    assert not out.exists(),'Use an absent output directory'
    before_files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in packet.rglob('*') if p.is_file()}
    expected=json.loads((packet/'toolkit-module-manifest.json').read_text())
    for name,want in expected.items():assert hashlib.sha256((toolkit/name).read_bytes()).hexdigest()==want,name
    receiving=json.loads((packet/'receiving.json').read_text());pins=receiving['local_fixture_commits']
    out.mkdir(parents=True);repo=out/'source-snapshots';native_tmp=out/'native-tmp';native_tmp.mkdir()
    env={k:v for k,v in os.environ.items() if not k.startswith('TESTPILOT_') and not k.startswith('GIT_')}
    env.update(PYTHONPATH=str(toolkit),PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(native_tmp),GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_NOSYSTEM='1',GIT_TERMINAL_PROMPT='0')
    def command(argv):
        r=subprocess.run(argv,env=env,capture_output=True,timeout=90)
        assert r.returncode==0,(argv,r.returncode,r.stderr.decode(errors='replace')[-2000:]);return r.stdout
    command(['git','clone','-q',str(packet/'source-snapshots.bundle'),str(repo)])
    for phase in ['before','after']:
        raw=command(['git','-C',str(repo),'archive',pins[phase]])
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            for name,want in receiving['source_provenance']['source_files'][phase].items():
                assert hashlib.sha256(archive.extractfile(name).read()).hexdigest()==want,(phase,name)
    argv=[sys.executable,'-B','-m','testpilot','regression','--repo',str(repo),'--report',str(packet/'generated/report.json'),
          '--before',pins['before'],'--after',pins['after'],'--python',str(a.python.absolute()),'--timeout','30','--out',str(out/'regression')]
    printed=command(argv);(out/'regression.stdout').write_bytes(printed)
    r=json.loads((out/'regression/regression.json').read_text())
    assert r['status']=='verified_regression' and r['model_calls']==0
    assert len(r['comparison']['witnesses'])==1
    assert r['before']['result']['generated']['passed']==1 and r['before']['result']['generated']['failed']==1
    assert r['after']['result']['generated']['passed']==2 and r['after']['result']['generated']['failed']==0
    assert command(['git','-C',str(repo),'status','--porcelain'])==b''
    assert {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in packet.rglob('*') if p.is_file()}==before_files
    receipt={'status':'ACCEPT','observed_at_utc':datetime.now(timezone.utc).isoformat(),'source_package_files_verified':80,
             'exact_toolkit_modules_verified':len(expected),'local_fixture_commits':pins,'regression_status':r['status'],
             'regression_model_calls':0,'witnesses':r['comparison']['witnesses'],'packet_and_clone_worktree_preserved':True}
    (out/'replay-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
