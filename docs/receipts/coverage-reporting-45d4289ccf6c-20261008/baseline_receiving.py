"""Exercise a real configured Coverage.py report and TestPilot public CLI.
Usage: python baseline_receiving.py SOURCE NEW_OUTPUT
Only authored local fixtures; no model-provider calls.
"""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, sys, time

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inventory(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("source",type=Path)
    ap.add_argument("output",type=Path)
    a=ap.parse_args()
    source=a.source.resolve(); out=a.output.resolve(); out.mkdir(exist_ok=False)
    env=dict(os.environ)
    for key in list(env):
        if key.startswith("TESTPILOT_"):
            env.pop(key)
    env.update(PYTHONPATH=str(source),PYTHONDONTWRITEBYTECODE="1",
               PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    source_before=inventory(source)
    executions=[]
    def run(label,argv,cwd):
        t=time.monotonic()
        p=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,text=True,timeout=90)
        (out/(label+".stdout.txt")).write_text(p.stdout)
        (out/(label+".stderr.txt")).write_text(p.stderr)
        executions.append({"name":label,"argv":argv,"cwd":str(cwd),
                           "exit":p.returncode,"seconds":round(time.monotonic()-t,3)})
        return p

    code='def classify(value):\n    if value >= 0:\n        return "nonnegative"\n    return "negative"\n'
    diff='diff --git a/calc.py b/calc.py\n--- a/calc.py\n+++ b/calc.py\n@@ -1,4 +1,4 @@\n def classify(value):\n     if value >= 0:\n-        return "positive"\n+        return "nonnegative"\n     return "negative"\n'
    reports={}
    inputs={}
    for name,threshold in (("threshold",100),("ordinary",0)):
        fixture=out/name/"fixture"; fixture.mkdir(parents=True)
        (fixture/"tests").mkdir()
        (fixture/"calc.py").write_text(code)
        (fixture/".coveragerc").write_text("[report]\nfail_under = "+str(threshold)+"\n")
        (fixture/"tests/test_existing.py").write_text('from calc import classify\n\ndef test_nonnegative():\n    assert classify(1) == "nonnegative"\n')
        script_dir=out/name/"script"; script_dir.mkdir()
        (script_dir/"01_plan.md").write_text("Check the negative input branch.\n")
        (script_dir/"02_tests.md").write_text('```python path=tests/test_negative.py\nfrom calc import classify\n\ndef test_negative():\n    assert classify(-1) == "negative"\n```\n')
        diff_path=out/name/"change.diff"; diff_path.write_text(diff)
        before=inventory(fixture)
        if name=="threshold":
            data=out/"oracle.coverage"
            p=run("oracle-run",[sys.executable,"-m","coverage","run","--data-file="+str(data),
                  "--source="+str(fixture),"--omit=*/tests/*","-m","pytest","-q","-p","no:cacheprovider"],fixture)
            assert p.returncode==0,(p.stdout,p.stderr)
            p=run("oracle-json",[sys.executable,"-m","coverage","json","--data-file="+str(data),
                  "-o",str(out/"oracle.json"),"-q"],fixture)
            oracle=json.loads((out/"oracle.json").read_text())
            assert p.returncode==2,(p.stdout,p.stderr)
            assert oracle["totals"]["percent_covered"]==75.0,oracle["totals"]
        user_out=out/name/"user-output"
        p=run(name+"-cli",[sys.executable,"-m","testpilot","run","--repo",str(fixture),
              "--diff",str(diff_path),"--backend","scripted","--script",str(script_dir),
              "--rounds","0","--timeout","30","--out",str(user_out)],out)
        assert p.returncode==0,(p.stdout,p.stderr)
        report=json.loads((user_out/"report.json").read_text())
        assert report["status"]=="passed" and report["final"]["passed"]==2,report
        assert inventory(fixture)==before,"source fixture changed"
        reports[name]={"coverage":report["coverage"],"status":report["status"],
                       "tests_passed":report["final"]["passed"],"tests_written":report["tests_written"],
                       "report_sha256":sha(user_out/"report.json"),"patch_sha256":sha(user_out/"testpilot.patch"),
                       "markdown":(user_out/"report.md").read_text()}
        inputs[name]=before
    unchanged=inventory(source)==source_before
    assert unchanged,"frozen source changed"
    defect=reports["threshold"]["coverage"]["total_before"]==0.0
    assert reports["ordinary"]["coverage"]["total_before"]==75.0
    receipt={"schema":"testpilot-configured-coverage-receiving/1",
             "python":sys.version,"executable":sys.executable,
             "pytest_version":__import__("pytest").__version__,
             "coverage_version":__import__("coverage").__version__,
             "source":str(source),"source_hashes":source_before,
             "oracle_total_before":75.0,"oracle_json_exit":2,
             "source_unchanged":unchanged,"fixture_hashes":inputs,
             "reported":reports,"executions":executions,
             "defect_reproduced":defect,
             "expected":{"total_before":75.0,"total_after":100.0,"total_delta":25.0},
             "limits":["Authored local projects and ScriptedModel responses only",
                       "No real provider, repository or deployed service effects",
                       "No change to source policy or coverage configuration"]}
    data=(json.dumps(receipt,indent=2,sort_keys=True)+"\n").encode()
    (out/"receipt.json").write_bytes(data)
    print(json.dumps({"defect_reproduced":defect,"threshold":reports["threshold"]["coverage"],
                      "ordinary":reports["ordinary"]["coverage"],"receipt":str(out/"receipt.json"),
                      "sha256":hashlib.sha256(data).hexdigest(),"all_fixtures_unchanged":True}))
if __name__=="__main__":
    main()
