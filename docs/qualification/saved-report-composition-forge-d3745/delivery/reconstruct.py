import base64, hashlib, json, os, pathlib, platform, stat, subprocess, sys
from datetime import datetime, timezone
root = pathlib.Path(__file__).resolve().parent
packet_path = root / "input-packet.json"
packet_bytes = packet_path.read_bytes()
assert len(packet_bytes) == 286528
assert hashlib.sha256(packet_bytes).hexdigest() == "2f0be575c1885efd93a70e88eeba544b5da591b1dfcfde7bfc08b0dec00170f2"
packet = json.loads(packet_bytes)
def identity(data):
    return {"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),"git_blob":hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()}
stage = root / "source"
stage.mkdir()
before = []
for item in packet["base"] + packet["donor"]:
    relative = pathlib.PurePosixPath(item["path"])
    assert not relative.is_absolute() and ".." not in relative.parts
    body = item["content"].encode("utf-8")
    ident = identity(body)
    assert ident["git_blob"] == item["sha"], (item["path"], ident)
    dest = stage / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("xb") as stream: stream.write(body)
    os.chmod(dest, int(item["mode"],8) & 0o777)
    before.append({"path":item["path"],"origin_commit":item["origin_commit"],"mode":stat.S_IMODE(dest.stat().st_mode),**ident})
report = stage / "eval/results/calc_clamp/report.json"
patch = stage / "eval/results/calc_clamp/testpilot.patch"
assert identity(report.read_bytes())["sha256"] == "00ce7170150b268cf7484de03658cb4af8f61bcdd64f1500dee46dfe004d52ac"
assert identity(patch.read_bytes())["sha256"] == "271ea1507ff20439503261e59984ce8d8e04cbf72a6d85c0e2dca7a05b9bf4bc"
output = root / "testpilot-saved-report-current-example.html"
command = [sys.executable,"-B","-m","testpilot.saved_report","--report",str(report),"--patch",str(patch),"--out",str(output)]
started = datetime.now(timezone.utc).isoformat()
result = subprocess.run(command,cwd=stage,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"},capture_output=True,timeout=30)
(root/"reconstruction.stdout").write_bytes(result.stdout)
(root/"reconstruction.stderr").write_bytes(result.stderr)
assert result.returncode == 0, (result.returncode,result.stderr)
assert not result.stderr
received = json.loads(result.stdout)
body = output.read_bytes()
actual = identity(body)
assert actual["bytes"] == 39385
assert actual["sha256"] == "b70d5a30d79b56fab426ed230ff47be2b375b6f448cf8482dd0e37ea0905f674"
assert received["sha256"] == actual["sha256"]
after = [{"path":e["path"],"origin_commit":e["origin_commit"],"mode":stat.S_IMODE((stage/e["path"]).stat().st_mode),**identity((stage/e["path"]).read_bytes())} for e in before]
assert before == after
names = sorted(str(p.relative_to(stage)) for p in stage.rglob("*") if p.is_file())
assert names == sorted(e["path"] for e in before)
receipt = {
 "schema":"hamon.root.testpilot.delivery-copy-reconstruction.v1",
 "accepted":True,
 "scope":"A new cloud delivery copy rendered once from exact published current-source/donor and saved artifact bytes. Its size and SHA-256 match the previously recorded native output. This is not retrieval of the native HTML, a replacement for the original receiving course, or browser qualification.",
 "started_utc":started,"finished_utc":datetime.now(timezone.utc).isoformat(),
 "platform":platform.platform(),"python":sys.version,"source_packet":{"git_blob":"ea6eea8aa1365cba5ecca94babc7437d858864cc",**identity(packet_bytes)},
 "source_commit":"7cbef6964dbb32518c189ad1498a031da33037ba","adoption_commit":"6f0aa5d9c4394d0f104a7b8b164c5765c2529f9c",
 "prior_native_receipt_git_blob":"9e10aa5b1305ce24e92e2cc5272f2634a94431ef",
 "prior_native_output":{"path":"/home/jacob/hamon/receiving/forge-d3745-testpilot-saved-review/consumer/review.html","bytes":39385,"sha256":"b70d5a30d79b56fab426ed230ff47be2b375b6f448cf8482dd0e37ea0905f674","mode":384},
 "command":command,"cwd":str(stage),"returncode":result.returncode,
 "stdout":identity(result.stdout),"stderr":identity(result.stderr),"cli_receipt":received,
 "output":{"path":str(output),"mode":stat.S_IMODE(output.stat().st_mode),**actual},
 "checks":{"exact_packet":True,"all26_source_git_identities":True,"exact_archived_pair":True,"successful_cli":True,"native_size_and_sha256_match":True,"all_source_bytes_modes_names_preserved":True},
 "sources":before
}
receipt_path = root/"reconstruction-receipt.json"
receipt_path.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps({"accepted":True,"output":receipt["output"],"receipt":{"path":str(receipt_path),**identity(receipt_path.read_bytes())},"commands":1,"source_files":len(before),"scope":receipt["scope"]}))

