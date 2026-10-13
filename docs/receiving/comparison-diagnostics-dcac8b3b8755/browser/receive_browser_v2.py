import argparse,base64,datetime,getpass,hashlib,importlib.metadata,json,os,pathlib,platform,tempfile,traceback
from playwright.sync_api import sync_playwright
ap=argparse.ArgumentParser()
ap.add_argument("--packet",required=True);ap.add_argument("--packet-git",required=True)
ap.add_argument("--output",required=True);ap.add_argument("--mode",choices=["original","candidate"],required=True)
ap.add_argument("--chrome",required=True)
a=ap.parse_args();out=pathlib.Path(a.output);out.mkdir(exist_ok=False)
temp=out.parent/(out.name+"-browser-temp");temp.mkdir(exist_ok=False)
os.environ["TEMP"]=str(temp);os.environ["TMP"]=str(temp);tempfile.tempdir=str(temp)
def ident(p):
 b=p.read_bytes();s=p.stat();return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"git":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest(),"mode":s.st_mode,"mtime_ns":str(s.st_mtime_ns),"inode":str(s.st_ino)}
def snap(folder):
 return {p.relative_to(folder).as_posix():ident(p) for p in sorted(folder.rglob("*")) if p.is_file()}
r={"schema":"hamon.testpilot-diagnostics-browser/1","utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"mode":a.mode,"host":platform.node(),"user":getpass.getuser(),"python":platform.python_version(),"playwright":importlib.metadata.version("playwright"),"passed":False,"checks":[],"requests":[],"page_errors":[],"console_errors":[],"downloads":[],"managed_disconnect":False,"browser_os_exit":"not measured"}
def check(name,actual,expected):
 ok=actual==expected;r["checks"].append({"name":name,"actual":actual,"expected":expected,"passed":ok})
 if not ok:raise RuntimeError(name)
pw=browser=context=None;watched={};intake=None
try:
 packet_path=pathlib.Path(a.packet)
 check("packet identity",ident(packet_path)["git"],a.packet_git)
 watched={str(p):ident(p) for p in (packet_path,pathlib.Path(__file__))}
 packet=json.loads(packet_path.read_bytes())
 intake=out/"intake";intake.mkdir()
 for item in packet["files"]:
  rel=pathlib.PurePosixPath(item["path"])
  if rel.is_absolute() or ".." in rel.parts:raise RuntimeError("Unsafe intake path")
  data=base64.b64decode(item["base64"],validate=True);expected=item["identity"]
  check("member "+item["path"],[len(data),hashlib.sha256(data).hexdigest(),hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()],[expected["bytes"],expected["sha256"],expected["git"]])
  dest=intake.joinpath(*rel.parts);dest.parent.mkdir(parents=True,exist_ok=True)
  with dest.open("xb") as f:f.write(data)
 criteria=json.loads((intake/"criteria.json").read_bytes())
 r["intake_before"]=snap(intake);r["watched_before"]=watched
 (out/"downloads").mkdir()
 pw=sync_playwright().start()
 browser=pw.chromium.launch(executable_path=a.chrome,headless=True)
 browser.on("disconnected",lambda:r.update(managed_disconnect=True))
 r["chrome"]=browser.version
 context=browser.new_context(java_script_enabled=False,accept_downloads=True,viewport={"width":1280,"height":900})
 context.on("request",lambda req:r["requests"].append({"url":req.url,"method":req.method}))
 context.route("http://**/*",lambda route:route.abort());context.route("https://**/*",lambda route:route.abort())
 for spec in criteria["pages"]:
  page=context.new_page()
  page.on("pageerror",lambda e:r["page_errors"].append(str(e)))
  page.on("console",lambda msg:r["console_errors"].append(msg.text) if msg.type=="error" else None)
  page.goto((intake/"pages"/(spec["name"]+".html")).as_uri(),wait_until="load",timeout=30000)
  check(spec["name"]+" no script",page.locator("script").count(),0)
  check(spec["name"]+" inert markup",page.locator("#diagnostics img,#diagnostics b").count(),0)
  check(spec["name"]+" CSP",page.locator('meta[http-equiv="Content-Security-Policy"]').get_attribute("content"),"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'")
  columns=page.locator("#diagnostics > .columns > div")
  check(spec["name"]+" columns",columns.count(),2)
  for side,cases in enumerate(spec["cases"]):
   col=columns.nth(side);details=col.locator(":scope > details")
   case_details=col.locator("details").filter(has=page.locator("summary > .pill"))
   check(spec["name"]+" count "+str(side),case_details.count(),len(cases))
   check(spec["name"]+" initial disclosure "+str(side),case_details.evaluate_all("(ds)=>ds.map(d=>d.open)"),spec["initial_"+a.mode][side])
   actual=[]
   for i,case in enumerate(cases):
    d=case_details.nth(i)
    outcome=d.locator("summary > .pill").text_content()
    nodeid=d.locator("summary").evaluate("(s)=>Array.from(s.childNodes).filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join('')")
    actual.append([outcome,nodeid])
    expected_message=criteria["visible_literal_message"] if case["message"]==criteria["literal_message"] else case["message"]
    if case["message"]:check(spec["name"]+" literal "+str(side)+"/"+str(i),d.locator(".detail pre code").text_content(),expected_message)
    else:check(spec["name"]+" empty "+str(side)+"/"+str(i),d.locator(".detail").inner_text().strip().endswith("No diagnostic text recorded."),True)
    check(spec["name"]+" attribution "+str(side)+"/"+str(i),d.locator(".detail > .meta").text_content(),"Generated file: "+(case["generated_file"] or "Not attributed to a generated file"))
   check(spec["name"]+" ordered occurrences "+str(side),actual,[[c["outcome"],c["nodeid"]] for c in cases])
  rows=page.locator("#results tbody tr").evaluate_all("(rs)=>rs.map(r=>Array.from(r.children).map(c=>c.textContent))")
  junit=next(row for row in rows if row[0]=="JUnit availability")
  check(spec["name"]+" JUnit labels",junit[1:],spec["junit"])
  if spec["name"]=="incomplete":
   check("final None placeholder",columns.nth(1).locator(".empty").inner_text(),"No final test result is recorded.")
  for index,label in enumerate(spec["junit"]):
   if label!="Available":
    for rowname in ("Complete-suite recorded counts","Generated-case recorded counts"):
     check(spec["name"]+" unavailable "+rowname+"/"+str(index),next(row for row in rows if row[0]==rowname)[index+1],"Unavailable as complete execution evidence")
  if spec["name"]=="mixed":
   target=columns.nth(0).locator("details").filter(has=page.locator("summary > .pill")).first
   summary=target.locator("summary")
   page.locator("body").click(position={"x":1,"y":1})
   focused=False
   for _ in range(100):
    page.keyboard.press("Tab")
    if summary.evaluate("(s)=>document.activeElement===s"):focused=True;break
   check("native Tab reaches first diagnostic",focused,True)
   start=target.evaluate("(d)=>d.open")
   page.keyboard.press("Enter");check("native Enter toggles",target.evaluate("(d)=>d.open"),not start)
   page.keyboard.press("Enter");check("native Enter restores",target.evaluate("(d)=>d.open"),start)
   # A click also changes the native disclosure without JavaScript.
   summary.click();check("native summary click",target.evaluate("(d)=>d.open"),not start)
   summary.click();check("native summary click restore",target.evaluate("(d)=>d.open"),start)
   page.set_viewport_size({"width":390,"height":844})
   target.scroll_into_view_if_needed()
   check("390px document width",page.evaluate("()=>document.documentElement.scrollWidth"),390)
   page.screenshot(path=str(out/"diagnostics-390.png"),full_page=False)
   page.set_viewport_size({"width":1280,"height":900})
   target.scroll_into_view_if_needed();page.screenshot(path=str(out/"diagnostics-desktop.png"),full_page=False)
   for role,fixture in (("before",spec["before"]),("after",spec["after"])):
    with page.expect_download(timeout=15000) as pending:page.locator("#download-"+role).click()
    download=pending.value
    check(role+" download filename",download.suggested_filename,role+"-report.json")
    path=out/"downloads"/(role+"-report.json");download.save_as(str(path))
    check(role+" exact download",path.read_bytes()==(intake/"fixtures"/fixture).read_bytes(),True)
    r["downloads"].append({"role":role,"identity":ident(path)})
  screen_states=page.locator("#diagnostics details").evaluate_all("(ds)=>ds.map(d=>d.open)")
  page.emulate_media(media="print")
  check(spec["name"]+" full print contents",page.locator("#diagnostics details > .detail").evaluate_all("(ds)=>ds.every(d=>d.getBoundingClientRect().height>0)"),True)
  page.emulate_media(media="screen")
  check(spec["name"]+" print restores disclosure",page.locator("#diagnostics details").evaluate_all("(ds)=>ds.map(d=>d.open)"),screen_states)
  storage=page.evaluate("()=>{try{return {local:localStorage.length,session:sessionStorage.length}}catch(e){return {unavailable:e.name}}}")
  r.setdefault("storage_observations",[]).append(storage)
  if "unavailable" not in storage:check(spec["name"]+" empty local/session storage",storage,{"local":0,"session":0})
  page.close()
 check("no external requests",[x for x in r["requests"] if x["url"].startswith(("http://","https://"))],[])
 check("no page errors",r["page_errors"],[]);check("no console errors",r["console_errors"],[])
 check("empty context storage",context.storage_state(),{"cookies":[],"origins":[]})
 r["passed"]=True
except BaseException as e:
 r["error"]=type(e).__name__+": "+str(e);r["traceback"]=traceback.format_exc()
finally:
 if context is not None:
  try:context.close()
  except BaseException as e:r["context_close_error"]=repr(e);r["passed"]=False
 if browser is not None:
  try:browser.close()
  except BaseException as e:r["browser_close_error"]=repr(e);r["passed"]=False
 if pw is not None:
  try:pw.stop()
  except BaseException as e:r["playwright_stop_error"]=repr(e);r["passed"]=False
 try:
  if intake is not None and "intake_before" in r:
   r["intake_after"]=snap(intake);check("complete intake conservation",r["intake_after"],r["intake_before"])
  if watched:
   r["watched_after"]={p:ident(pathlib.Path(p)) for p in watched};check("driver/packet conservation",r["watched_after"],watched)
  if browser is not None:check("managed browser disconnected",r["managed_disconnect"],True)
 except BaseException as e:r["conservation_or_cleanup_error"]=repr(e);r["passed"]=False
 raw=(json.dumps(r,ensure_ascii=False,indent=2)+"\n").encode("utf-8");(out/"receiving.json").write_bytes(raw)
 print(json.dumps({"passed":r["passed"],"checks":len(r["checks"]),"downloads":len(r["downloads"]),"receipt":ident(out/"receiving.json"),"error":r.get("error"),"managed_disconnect":r["managed_disconnect"]}))
raise SystemExit(0 if r["passed"] else 1)
