"""Rerun only the four environment-affected controls against unchanged composition."""
import hashlib,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
root=Path("/home/jacob/testpilot-coverage-45d4289ccf6c")
source=root/"composition-dcd353-worktree"
evidence=root/"composition-dcd353-evidence"
tree=subprocess.check_output(["git","-C",str(source),"write-tree"],text=True).strip()
assert tree=="08d13653668d58660cbf3614108ba79ddd8f3b17",tree
subprocess.run(["git","-C",str(source),"diff","--quiet"],check=True)
receiver=root/"run_receiving.py"
assert hashlib.sha256(receiver.read_bytes()).hexdigest()=="8755aaea0cde012820762e306be7b7f2d607cd3ae7f1ec3a5aa030452af148c1"
argv=[str(root/"composition-receiving-venv/bin/python"),"-B",str(receiver),str(source),str(evidence/"selected-python-aligned"),str(source/"tests/test_cli_python.py")+"::test_project_environment_runs_baseline_generation_and_repair"]
launch={"started_utc":datetime.now(timezone.utc).isoformat(),"command":argv,"source_tree":tree,"receiver_sha256":hashlib.sha256(receiver.read_bytes()).hexdigest(),"tooling_manifest_sha256":hashlib.sha256((evidence/"aligned-tooling-manifest.json").read_bytes()).hexdigest(),"scope":"Only the four existing prepared_python spellings that failed from unavailable selected-interpreter coverage; no source/test changes and no other cases rerun."}
(evidence/"selected-python-aligned-launch.json").write_text(json.dumps(launch,indent=2)+"\n")
env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1")
run=subprocess.run(argv,text=True,capture_output=True,env=env,timeout=360)
(evidence/"selected-python-aligned-driver.stdout.txt").write_text(run.stdout)
(evidence/"selected-python-aligned-driver.stderr.txt").write_text(run.stderr)
result={"finished_utc":datetime.now(timezone.utc).isoformat(),"exit":run.returncode,"stdout":run.stdout,"stderr":run.stderr}
(evidence/"selected-python-aligned-result.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
raise SystemExit(run.returncode)
