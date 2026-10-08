"""Independent PR20 composition/recorded-behavior verification; no native execution."""
from pathlib import Path
from html.parser import HTMLParser
import argparse, ast, base64, hashlib, json, tarfile, types

def check(value,message):
    if not value:raise RuntimeError(message)
def digest(data):
    return {"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.tables=[];self.pres=[];self.downloads={}
        self.table=None;self.row=None;self.cell=None;self.pre=None;self.text=[]
    def handle_starttag(self,tag,attrs):
        attr=dict(attrs)
        if tag=="table":self.table=[]
        elif tag=="tr":self.row=[]
        elif tag in ("td","th"):self.cell=""
        elif tag=="pre":self.pre=""
        elif tag=="a" and attr.get("download"):
            self.downloads[attr["download"]]=base64.b64decode(attr["href"].split(";base64,",1)[1],validate=True)
    def handle_data(self,data):
        self.text.append(data)
        if self.cell is not None:self.cell+=data
        if self.pre is not None:self.pre+=data
    def handle_endtag(self,tag):
        if tag in ("td","th") and self.cell is not None:self.row.append(self.cell);self.cell=None
        elif tag=="tr" and self.row is not None:self.table.append(self.row);self.row=None
        elif tag=="table" and self.table is not None:self.tables.append(self.table);self.table=None
        elif tag=="pre" and self.pre is not None:self.pres.append(self.pre);self.pre=None
def main():
    ap=argparse.ArgumentParser();ap.add_argument("archive",type=Path);args=ap.parse_args()
    here=Path(__file__).resolve().parent
    raw=args.archive.read_bytes()
    check(digest(raw)=={"bytes":1077732,"sha256":"8f480e0b9edb7bfa29c4e75bbcf8f5298e9d735fdc3ca0a65205dd6b3bb0670a"},"Wrong author supplement")
    tree=json.loads((here/"current-tree.json").read_text())
    leaves={x["path"]:x for x in tree["tree"] if x["type"]=="blob"}
    check(tree["sha"]=="2045a73704f752d374704657fccf90fd5e774258" and not tree["truncated"],"Wrong canonical tree")
    frozen=json.loads((here/"reviewed-source-manifest.json").read_text())
    prior={x["path"]:x for x in frozen["files"]}
    module=types.ModuleType("original_receiving_helpers")
    helper=(here/"original-verify_review.py").read_bytes()
    check(digest(helper)["sha256"]=="0e66baf6cfa6f25daf6c89bf6d5a7b4caed2c1f5d614553531dc64b58d01780d","Changed original helper")
    exec(compile(helper,"original-verify_review.py","exec"),module.__dict__)
    with tarfile.open(args.archive) as archive:
        members=archive.getmembers()
        check(len(members)==134 and all(x.isfile() for x in members),"Unexpected native members")
        check(len({x.name for x in members})==len(members),"Duplicate member")
        def data(name):return archive.extractfile(name).read()
        def obj(name):return json.loads(data(name))
        manifest=obj("native-manifest.json")
        check(digest(data("native-manifest.json"))["sha256"]=="09e516e12f09ff72bbe8dbbaee3fbcd7e1041a9e9bc9acd640ae8c313b79f334","Changed native manifest")
        artifacts=manifest["artifacts"]
        for row in artifacts:
            check(digest(data(row["path"]))=={k:row[k] for k in ("bytes","sha256")},"Artifact mismatch: "+row["path"])
        check({x.name for x in members}=={x["path"] for x in artifacts}|{"native-manifest.json"},"Manifest member set differs")
        source=obj("source-manifest.json")
        check(data("source-manifest.json")==(here/"source-manifest.json").read_bytes(),"Source manifest differs")
        for row in source["files"]:
            b=data("source/"+row["path"]);git=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
            check(digest(b)=={k:row[k] for k in ("bytes","sha256")} and git==row["git_blob"],"Changed source")
            if row["path"] not in source["scope_paths"]:
                leaf=leaves[row["path"]]
                check((git,len(b),row["mode"])==(leaf["sha"],leaf["size"],leaf["mode"]),"Changed unowned current file")
            elif row["path"] in source["unchanged_frozen_files"]:
                check(row["sha256"]==prior[row["path"]]["sha256"],"Changed reviewed file")
        current=(here/"current-loop.py").read_bytes()
        composed=data("source/testpilot/loop.py")
        restored=composed
        replacements=[
            (b"from .html_report import render_html_report\n",b""),
            (b'    paths = {"patch": out / "testpilot.patch", "json": out / "report.json", "md": out / "report.md",\n             "html": out / "report.html"}\n',b'    paths = {"patch": out / "testpilot.patch", "json": out / "report.json", "md": out / "report.md"}\n'),
            (b'    paths["html"].write_text(render_html_report(paths["json"].read_bytes(), paths["patch"].read_bytes()), encoding="utf-8")\n',b"")]
        for needle,replacement in replacements:
            check(restored.count(needle)==1,"Reviewed writer addition differs");restored=restored.replace(needle,replacement)
        check(restored==current==data("upstream/testpilot/loop.py"),"Current loop not preserved")
        reviewed=(here/"reviewed-README.md").read_bytes()
        start=reviewed.index(b"## Review your own run in a browser\n")
        end=reviewed.index(b"## Running on Nebius Token Factory\n",start)
        section=reviewed[start:end];doc=data("source/README.md")
        check(doc.count(section)==1 and doc.replace(section,b"",1)==data("upstream/README.md")==(here/"current-README.md").read_bytes(),"Current README not preserved")
        def definitions(code):
            return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(code).body if isinstance(n,(ast.ClassDef,ast.FunctionDef))}
        before,after=definitions(current),definitions(composed)
        check(set(before)==set(after) and [n for n in before if before[n]!=after[n]]==["write_outputs"],"Other loop behavior differs")
        invocations=obj("commands/invocations.json")
        check(len(invocations)==3 and all(x["exit_code"]==0 for x in invocations),"Native command did not pass")
        cli=obj("cli/report.json");browser=obj("browser/report.json")
        check(cli["source_before"]==cli["source_after"],"Source changed during author capture")
        check(cli["driver_sha256"]==digest(data("capture_allocator_compatibility.py"))["sha256"],"CLI driver binding differs")
        check(browser["captureReportSha256"]==digest(data("cli/report.json"))["sha256"],"Browser CLI capture binding differs")
        check(browser["driverSha256"]==digest(data("check_browser.mjs"))["sha256"]==prior["docs/receiving/html-report-066deeadcc8b/check_browser.mjs"]["sha256"],"Browser driver changed")
        check(len(browser["checks"])==39 and all(x["passed"] and x["actual"]==x["expected"] for x in browser["checks"]),"Recorded browser checks disagree")
        unit="tests/unit/test_calc_testpilot.py";integration="tests/integration/test_calc_testpilot_2.py"
        expected_generated={"collected":2,"passed":2,"failed":0,"error":0,"skipped":0}
        table_count=cell_count=download_count=0;results=[]
        for record in cli["cases"]:
            name=record["name"];report=obj("cli/"+name+"/out/report.json")
            check(record["exit_code"]==0 and report["status"]=="passed" and report["final"]["returncode"]==0,"Wrong native outcome")
            check(report["final"]["passed"]==3 and report["final"]["generated"]==expected_generated,"Actual collection differs")
            check(set(report["test_files"])=={unit,integration} and "legacy/test_calc.py" not in report["test_files"],"Module identity collided")
            for path,pin in record["inputs"].items():check(digest(data("cli/"+name+"/repo/"+path))==pin,"Input custody differs")
            for filename,pin in record["artifacts"].items():check(digest(data("cli/"+name+"/out/"+filename))==pin,"CLI artifact hash differs")
            html=data("cli/"+name+"/out/report.html")
            check(html==data("browser/isolated-pages/"+name+".html"),"Detached document differs")
            document=Document();document.feed(html.decode())
            expected=module.tables_from_report(report)
            check(document.tables==expected,"Rendered table differs from captured JSON")
            table_count+=len(expected);cell_count+=sum(len(row) for table in expected for row in table[1:])
            for value in report["test_files"].values():check(value in document.pres,"Final source missing")
            for r in report["rounds"]:
                for value in r["contents"].values():check(value in document.pres,"Round source missing")
                for warning in r["warnings"]:check(warning in "".join(document.text),"Mapping warning missing")
            if name=="repair":
                first,last=report["rounds"]
                check(report["repair_rounds_used"]==1 and first["result"]["failed"]==1 and last["result"]["failed"]==0,"Repair outcome/history differs")
                check(first["contents"][unit]!=last["contents"][unit] and first["contents"][integration]==last["contents"][integration],"Partial repair did not retain the other file")
                script=data("cli/repair/script/03.md")
                check(b"tests/unit/test_calc.py" in script and unit.encode() not in script,"Repair did not use original suggestion alias")
            else:check(report["repair_rounds_used"]==0 and len(report["rounds"])==1,"Unexpected repair")
            for filename in ["report.json","testpilot.patch"]:
                original=data("cli/"+name+"/out/"+filename)
                check(document.downloads[filename]==original==data("browser/"+name+"-"+filename),"Actual/embedded download differs")
                download_count+=1
            results.append({"name":name,"generated_files":sorted(report["test_files"]),"total_passed":3,"generated_passed":2,"repairs":report["repair_rounds_used"],"html":digest(html)})
        result={"schema":"independent-testpilot-pr20-recomputed-v1","decision":"accepted","canonical_base":source["base"],"canonical_tree":tree["sha"],"canonical_leaves":len(leaves),"source_files":len(source["files"]),"current_unowned_files_exact":74,"current_loop_other_definitions_exact":len(before)-1,"current_loop_and_readme_reconstructed":True,"original_other_four_scoped_files_exact":True,"native_archive":digest(raw),"native_members_verified":len(members),"native_artifacts_verified":len(artifacts),"author_native_commands_received":len(invocations),"author_browser_checks_received":39,"independently_recomputed_html_tables":table_count,"independently_recomputed_data_cells":cell_count,"actual_downloads_received_byte_exact":download_count,"cases":results,"boundary":"Independent source reconstruction and archived raw-evidence recomputation. The author executed the two current CLI cases and browser; this receiver did not repeat a native product run."}
        print(json.dumps(result,indent=2))
if __name__=="__main__":main()
