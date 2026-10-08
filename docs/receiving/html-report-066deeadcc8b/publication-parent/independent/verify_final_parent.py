from pathlib import Path
import argparse, ast, hashlib, json, tarfile
def pin(data): return {"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
def blob(data): return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def check(ok,message):
    if not ok: raise RuntimeError(message)
def definitions(data):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(data).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("publication_parent",type=Path);ap.add_argument("pr20_archive",type=Path);a=ap.parse_args()
    here=Path(__file__).resolve().parent
    direct=json.loads((here/"direct-primary.json").read_bytes());commit=direct["commit"];tree=direct["tree"]
    check(commit["sha"]=="3e745e6b6a2f7e383fc6b43f12e69f7a221fb051" and commit["tree"]["sha"]==tree["sha"]=="56b8c198f3d88e133c6d641b0cc7c63de0dd6fcd" and not tree["truncated"],"Wrong primary parent/tree")
    leaves={x["path"]:x for x in tree["tree"] if x["type"]=="blob"}
    check(len(leaves)==728 and not any(x.endswith("AGENTS.md") for x in leaves),"Unexpected primary tree")
    parent=a.publication_parent
    raw_manifest=(parent/"source-manifest.json").read_bytes()
    check(pin(raw_manifest)["sha256"]=="82f428d63a5edf0fd1091ad83244ff0861eb5ac3356be8f6619474b703e61d0a","Changed publication manifest")
    manifest=json.loads(raw_manifest)
    author_tree=json.loads((parent/"current-tree-blobs.json").read_bytes())
    check({x["path"]:(x["sha"],x["mode"],x["size"]) for x in author_tree["tree"]}=={p:(x["sha"],x["mode"],x["size"]) for p,x in leaves.items()},"Author tree differs from direct primary retrieval")
    for path,text in direct["files"].items():
        data=text.encode();leaf=leaves[path]
        check((blob(data),len(data))==(leaf["sha"],leaf["size"]),"Primary file differs "+path)
        check(data==(parent/"upstream"/path).read_bytes(),"Author upstream differs "+path)
    for row in manifest["artifacts"]:
        data=(parent/row["path"]).read_bytes()
        check(pin(data)=={k:row[k] for k in ("bytes","sha256")} and blob(data)==row["git_blob"],"Changed author artifact "+row["path"])
    archive=a.pr20_archive
    check(pin(archive.read_bytes())=={"bytes":1077732,"sha256":"8f480e0b9edb7bfa29c4e75bbcf8f5298e9d735fdc3ca0a65205dd6b3bb0670a"},"Wrong native-qualified PR20 archive")
    scope=set(manifest["scope_paths"])
    check({x.relative_to(parent/"proposed").as_posix() for x in (parent/"proposed").rglob("*") if x.is_file()}==scope and len(scope)==6,"Unexpected proposed source scope")
    current=direct["files"]["testpilot/loop.py"].encode();proposed=(parent/"proposed/testpilot/loop.py").read_bytes()
    old=b'- Coverage: unavailable (install `coverage`)';new=b'- Coverage: unavailable'
    with tarfile.open(archive) as tar:
        prior=tar.extractfile("source/testpilot/loop.py").read()
        prior_parent=tar.extractfile("upstream/testpilot/loop.py").read()
        check(prior.count(old)==prior_parent.count(old)==1 and prior_parent.replace(old,new,1)==current and prior.replace(old,new,1)==proposed,"Only inherited Markdown wording may differ from native-qualified loops")
        for path in scope-{"testpilot/loop.py"}:
            check((parent/"proposed"/path).read_bytes()==tar.extractfile("source/"+path).read(),"Previously reviewed file changed "+path)
    restored=proposed
    additions=[
        (b"from .html_report import render_html_report\n",b""),
        (b'    paths = {"patch": out / "testpilot.patch", "json": out / "report.json", "md": out / "report.md",\n             "html": out / "report.html"}\n',b'    paths = {"patch": out / "testpilot.patch", "json": out / "report.json", "md": out / "report.md"}\n'),
        (b'    paths["html"].write_text(render_html_report(paths["json"].read_bytes(), paths["patch"].read_bytes()), encoding="utf-8")\n',b"")]
    for needle,replacement in additions:
        check(restored.count(needle)==1,"Writer addition differs");restored=restored.replace(needle,replacement,1)
    check(restored==current,"Current primary loop not reconstructed")
    readme=(parent/"proposed/README.md").read_bytes()
    start=readme.index(b"## Review your own run in a browser\n");end=readme.index(b"## Running on Nebius Token Factory\n",start)
    check(readme[:start]+readme[end:]==direct["files"]["README.md"].encode(),"Current README not reconstructed")
    before,after=definitions(current),definitions(proposed)
    check(set(before)==set(after) and [x for x in before if before[x]!=after[x]]==["write_outputs"],"Other current loop definitions changed")
    historical=definitions(prior_parent)
    check(set(historical)==set(before) and [x for x in before if historical[x]!=before[x]]==["render_report"],"Unrelated upstream loop behavior changed")
    print(json.dumps({"schema":"independent-testpilot-final-parent-v1","decision":"accepted for normal exact-head source integration gates","canonical_base":commit["sha"],"canonical_tree":tree["sha"],"canonical_leaves":len(leaves),"direct_primary_files":4,"author_manifest_artifacts_verified":len(manifest["artifacts"]),"proposed_scoped_files":len(scope),"native_qualified_scoped_files_unchanged":5,"only_loop_delta_since_native_qualification":"Inherited Markdown coverage-unavailable wording","current_loop_and_readme_reconstructed":True,"other_current_loop_definitions_exact":len(before)-1,"proposed_loop":pin(proposed),"proposed_readme":pin(readme),"upstream_model_and_sandbox":"Exact canonical primary bytes; not part of the six-path overlay.","boundary":"Independent source-only custody and reconstruction. Native CLI/browser qualification remains pinned to PR20 parent269e5533 and earlier freezes; no new runtime pass is attributed to this final parent."},indent=2))
if __name__=="__main__":main()
