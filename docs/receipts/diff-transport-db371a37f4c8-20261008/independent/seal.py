import hashlib,json,pathlib
r=pathlib.Path("/Users/me/hamon-testpilot-receiving-db371a37f4c8")
files=[]
for p in sorted(r.rglob('*')):
 if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and p.name!='manifest.json':
  b=p.read_bytes();files.append({'path':str(p.relative_to(r)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
(r/'manifest.json').write_text(json.dumps({'files':files,'filesCount':len(files),'bytes':sum(f['bytes'] for f in files)},indent=2))
print(json.dumps({'filesCount':len(files),'bytes':sum(f['bytes'] for f in files),'manifestSha256':hashlib.sha256((r/'manifest.json').read_bytes()).hexdigest()}))
