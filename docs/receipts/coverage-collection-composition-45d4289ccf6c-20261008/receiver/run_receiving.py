"""Run source-bound pytest receiving in one exclusive native output directory."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, sys, time
import xml.etree.ElementTree as ET

def hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("source",type=Path)
    ap.add_argument("output",type=Path)
    ap.add_argument("tests",nargs="+")
    a=ap.parse_args()
    source=a.source.resolve(); out=a.output.resolve(); out.mkdir(exist_ok=False)
    temps=out/"sandbox-temp"; temps.mkdir()
    env=dict(os.environ)
    env.update(PYTHONPATH=str(source),PYTHONDONTWRITEBYTECODE="1",PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",TMPDIR=str(temps))
    before=hashes(source)
    argv=[sys.executable,"-B","-m","pytest","-q","-p","no:cacheprovider","-o","addopts=",
          "--basetemp="+str(out/"fixtures"),"--junitxml="+str(out/"junit.xml"),*a.tests]
    t=time.monotonic()
    run=subprocess.run(argv,cwd=out,env=env,capture_output=True,text=True,timeout=300)
    (out/"stdout.txt").write_text(run.stdout)
    (out/"stderr.txt").write_text(run.stderr)
    cases=[]
    if (out/"junit.xml").is_file():
        for case in ET.parse(out/"junit.xml").iter("testcase"):
            outcome=next((label for tag,label in (("failure","failed"),("error","error"),("skipped","skipped"))
                          if case.find(tag) is not None),"passed")
            cases.append({"name":case.get("name"),"outcome":outcome})
    import coverage, pytest
    covroot=Path(coverage.__file__).parent
    receipt={"schema":"testpilot-coverage-pytest-receiving/1","source":str(source),
             "source_sha256":before,"source_unchanged":hashes(source)==before,
             "python":sys.version,"executable":sys.executable,"pytest":pytest.__version__,"coverage":coverage.__version__,
             "coverage_source_sha256":{name:hashlib.sha256((covroot/name).read_bytes()).hexdigest()
                                       for name in ("cmdline.py","control.py","jsonreport.py")},
             "argv":argv,"exit":run.returncode,"seconds":round(time.monotonic()-t,3),"cases":cases,
             "sandbox_temporary_children_after":[p.name for p in temps.iterdir()],
             "test_source_sha256":{path:hashlib.sha256(Path(path.split("::")[0]).read_bytes()).hexdigest() for path in a.tests}}
    data=(json.dumps(receipt,indent=2,sort_keys=True)+"\n").encode()
    (out/"receipt.json").write_bytes(data)
    print(json.dumps({"exit":run.returncode,"cases":cases,"source_unchanged":receipt["source_unchanged"],
                      "temporary_children":receipt["sandbox_temporary_children_after"],
                      "receipt_sha256":hashlib.sha256(data).hexdigest()}))
    assert receipt["source_unchanged"]
    assert not receipt["sandbox_temporary_children_after"]
    return run.returncode
if __name__=="__main__":
    raise SystemExit(main())
