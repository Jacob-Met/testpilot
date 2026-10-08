from pathlib import Path
import ast,hashlib,json,shutil
here=Path("/dev/shm/hamon-066deeadcc8b-research-testpilot-pr20-review")
author=Path("/dev/shm/hamon-066deeadcc8b-testpilot-html/composition-pr20")
old=Path("/dev/shm/hamon-066deeadcc8b-research-testpilot-review/candidate")
mbytes=(author/"source-manifest.json").read_bytes()
if hashlib.sha256(mbytes).hexdigest()!="510f4dc179c71970444e4e97389272b763b1ce3b1f6229d86e13c6a08769b29a":raise RuntimeError("Wrong manifest")
m=json.loads(mbytes);tree=json.loads((here/"current-tree.json").read_text())
if tree["sha"]!=m["tree"] or tree["truncated"]:raise RuntimeError("Wrong current tree")
leaves={x["path"]:x for x in tree["tree"] if x["type"]=="blob"}
rows=[]
for row in m["files"]:
 rel=row["path"];data=(author/"source"/rel).read_bytes()
 git=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
 if len(data)!=row["bytes"] or hashlib.sha256(data).hexdigest()!=row["sha256"] or git!=row["git_blob"]:raise RuntimeError("Changed frozen source: "+rel)
 if rel not in m["scope_paths"]:
  leaf=leaves[rel]
  if (git,len(data),row["mode"])!=(leaf["sha"],leaf["size"],leaf["mode"]):raise RuntimeError("Changed unowned current leaf: "+rel)
 elif rel in m["unchanged_frozen_files"] and data!=(old/rel).read_bytes():raise RuntimeError("Changed reviewed scope file: "+rel)
 rows.append(row)
import_line=b"from .html_report import render_html_report\n"
new_paths=b'    paths = {"patch": out / "testpilot.patch", "json": out / "report.json", "md": out / "report.md",\n             "html": out / "report.html"}\n'
old_paths=b'    paths = {"patch": out / "testpilot.patch", "json": out / "report.json", "md": out / "report.md"}\n'
write_line=b'    paths["html"].write_text(render_html_report(paths["json"].read_bytes(), paths["patch"].read_bytes()), encoding="utf-8")\n'
composed=(author/"source/testpilot/loop.py").read_bytes()
restored=composed
for needle,replacement in [(import_line,b""),(new_paths,old_paths),(write_line,b"")]:
 if restored.count(needle)!=1:raise RuntimeError("Reviewed writer addition differs")
 restored=restored.replace(needle,replacement)
current=(here/"current-loop.py").read_bytes()
if restored!=current:raise RuntimeError("Current loop does not reconstruct exactly")
start=(old/"README.md").read_text().index("## Review your own run in a browser\n")
end=(old/"README.md").read_text().index("## Running on Nebius Token Factory\n",start)
section=(old/"README.md").read_text()[start:end].encode()
doc=(author/"source/README.md").read_bytes()
if doc.count(section)!=1 or doc.replace(section,b"",1)!=(here/"current-README.md").read_bytes():raise RuntimeError("Current README does not reconstruct exactly")
for rel,filename in [("testpilot/loop.py","current-loop.py"),("README.md","current-README.md")]:
 data=(here/filename).read_bytes();leaf=leaves[rel]
 if hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()!=leaf["sha"] or len(data)!=leaf["size"]:raise RuntimeError("Primary current file is not tree-bound")
def definitions(data):
 return {x.name:ast.dump(x,include_attributes=False) for x in ast.parse(data).body if isinstance(x,(ast.ClassDef,ast.FunctionDef))}
a,z=definitions(current),definitions(composed)
different=[name for name in a if a[name]!=z.get(name)]
if set(a)!=set(z) or different!=["write_outputs"]:raise RuntimeError("Composition changed another definition")
(here/"source-manifest.json").write_bytes(mbytes)
(here/"composed-loop.py").write_bytes(composed)
(here/"composed-README.md").write_bytes(doc)
result={"schema":"independent-testpilot-pr20-source-composition-v1","canonical_base":m["base"],"canonical_tree":tree["sha"],"canonical_leaves":len(leaves),"reviewed_projection":m["reviewed_projection"],"source_manifest_sha256":hashlib.sha256(mbytes).hexdigest(),"source_files":len(rows),"unowned_current_files_exact":len(rows)-len(m["scope_paths"]),"four_other_reviewed_files_exact":m["unchanged_frozen_files"],"current_loop_reconstructed_byte_identically":True,"current_readme_reconstructed_byte_identically":True,"unchanged_current_loop_top_level_definitions":len(a)-1,"only_changed_definition":different,"composed_loop_sha256":hashlib.sha256(composed).hexdigest(),"composed_readme_sha256":hashlib.sha256(doc).hexdigest(),"agent_instruction_files":[p for p in leaves if p.endswith("AGENTS.md")]}
(here/"source-verification.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result))
