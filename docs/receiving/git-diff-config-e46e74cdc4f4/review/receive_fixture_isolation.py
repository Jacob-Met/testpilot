"""Native private-repository receiving for authored TestPilot fixture isolation."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

PROJECT=Path("/home/jacob/hamon-e46e74cdc4f4-testpilot")
ROOT=Path("/home/jacob/hamon-e46e74cdc4f4-testpilot-source-review")

def clean_env():
    env={k:v for k,v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1",GIT_CONFIG_GLOBAL=os.devnull,PYTHONDONTWRITEBYTECODE="1")
    return env

def child(source, output):
    sys.path.insert(0,str(PROJECT))
    spec=importlib.util.spec_from_file_location("received_git_fixture",source)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    case=module.GitDiffConfigurationTests("test_unchanged_project_retains_the_empty_result")
    result={"source":str(source),"setup_succeeded":False}
    try:
        case.setUp()
        result["setup_succeeded"]=True
        result["fixture_root"]=str(case.root)
        result["own_git_directory_exists"]=(case.repo/".git").is_dir()
        p=subprocess.run(["git","-C",str(case.repo),"rev-parse","--show-toplevel"],env=clean_env(),capture_output=True,text=True)
        result["native_own_repo_probe_exit"]=p.returncode
        result["native_own_repo_path"]=p.stdout.strip()
        if p.returncode==0:
            q=subprocess.run(["git","-C",str(case.repo),"show","HEAD:a/subject.py"],env=clean_env(),capture_output=True)
            result["own_commit_before_source"]=q.stdout.decode("utf-8","replace")
            result["own_working_source"]=(case.repo/"a/subject.py").read_text()
    except Exception as exc:
        result["exception"]=type(exc).__name__
        result["message"]=str(exc)
        result["traceback"]=traceback.format_exc()
        if hasattr(case,"repo"):
            result["fixture_root"]=str(case.root)
            result["own_git_directory_exists"]=(case.repo/".git").is_dir()
    finally:
        if hasattr(case,"temp"):
            case.tearDown()
    output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))
    return 0

def hashes(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}

def parent(source,label,expect_isolated):
    runroot=ROOT/("sentinel-"+label)
    runroot.mkdir()
    source_bytes=source.read_bytes()
    frozen=runroot/"received_test.py"
    frozen.write_bytes(source_bytes)
    rows=[]
    for route in ("all-repository-routing","index-only"):
        case_root=runroot/route
        case_root.mkdir()
        sentinel=case_root/"sentinel"
        sentinel.mkdir()
        (sentinel/"sentinel.txt").write_bytes(b"independent sentinel; do not change\n")
        env=clean_env()
        def git(*args):
            return subprocess.run(["git","-C",str(sentinel),*args],env=env,capture_output=True,check=True)
        git("init","-q")
        git("add",".")
        git("-c","user.name=Isolated Receiver","-c","user.email=fixture@invalid.local","-c","commit.gpgsign=false","commit","-qm","sentinel baseline")
        before=hashes(sentinel)
        tmp=case_root/"owned-temporary-directories"
        tmp.mkdir()
        childenv=dict(env)
        childenv.update(TMPDIR=str(tmp),TMP=str(tmp),TEMP=str(tmp),GIT_INDEX_FILE=str(sentinel/".git/index"))
        if route=="all-repository-routing":
            childenv.update(GIT_DIR=str(sentinel/".git"),GIT_WORK_TREE=str(sentinel))
        output=case_root/"child-receipt.json"
        result=subprocess.run([sys.executable,"-B",str(Path(__file__)),"--child",str(frozen),str(output)],env=childenv,capture_output=True,timeout=30)
        (case_root/"stdout.txt").write_bytes(result.stdout)
        (case_root/"stderr.txt").write_bytes(result.stderr)
        assert result.returncode==0,(result.returncode,result.stderr)
        received=json.loads(output.read_text())
        after=hashes(sentinel)
        changed=sorted(p for p in set(before)|set(after) if before.get(p)!=after.get(p))
        isolated=bool(received["setup_succeeded"] and received.get("own_git_directory_exists")
                      and received.get("native_own_repo_path")==str(Path(received["fixture_root"])/"project")
                      and received.get("own_commit_before_source")=="def answer():\n    return 1\n"
                      and received.get("own_working_source")=="def answer():\n    return 2\n"
                      and not changed)
        row={"route":route,"isolated":isolated,"fixture_receipt":received,
             "sentinel_changed_paths":changed,"before":before,"after":after}
        rows.append(row)
        assert isolated==expect_isolated,(route,isolated,expect_isolated)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==hashlib.sha256(source_bytes).hexdigest()
    record={"schema":"testpilot.git-fixture-isolation.receiving.v1","label":label,
            "accepted":True,"expect_isolated":expect_isolated,
            "source":{"path":str(source),"sha256":hashlib.sha256(source_bytes).hexdigest(),"bytes":len(source_bytes)},
            "cases":rows,"source_unchanged":True,"private_sentinels_only":True,
            "product_cli_run":False,"python":sys.version,"directory":str(runroot),
            "time_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    data=(json.dumps(record,indent=2)+"\n").encode()
    (runroot/"receipt.json").write_bytes(data)
    print(json.dumps({"label":label,"accepted":True,"directory":str(runroot),"source":record["source"],
                      "receipt_sha256":hashlib.sha256(data).hexdigest(),
                      "cases":[{"route":r["route"],"isolated":r["isolated"],
                                "setup_succeeded":r["fixture_receipt"]["setup_succeeded"],
                                "sentinel_changed_paths":r["sentinel_changed_paths"]} for r in rows]},indent=2))
    return 0

if __name__=="__main__":
    if sys.argv[1]=="--child":
        raise SystemExit(child(Path(sys.argv[2]),Path(sys.argv[3])))
    raise SystemExit(parent(Path(sys.argv[1]),sys.argv[2],sys.argv[3]=="isolated"))
