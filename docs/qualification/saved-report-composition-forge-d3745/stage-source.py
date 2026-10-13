import pathlib,json,hashlib,stat,datetime
root=pathlib.Path(__file__).resolve().parent
packet=json.loads((root/'input-packet.json').read_bytes())
assert len(packet['base'])==23 and len(packet['donor'])==3
for group in ['base','donor']:
 for r in packet[group]:
  p=pathlib.PurePosixPath(r['path']);assert not p.is_absolute() and '..' not in p.parts
  b=r['content'].encode('utf-8');assert hashlib.sha1(b'blob '+str(len(b)).encode()+bytes([0])+b).hexdigest()==r['sha']
assert not ({r['path'] for r in packet['base']}&{r['path'] for r in packet['donor']})
rows=[]
for directory,records in [('baseline',packet['base']),('combined',packet['base']+packet['donor'])]:
 target=root/directory;target.mkdir()
 for r in records:
  p=target/r['path'];p.parent.mkdir(parents=True,exist_ok=True)
  b=r['content'].encode('utf-8')
  with p.open('xb') as f:f.write(b)
  p.chmod(int(r['mode'],8)&0o777)
  assert p.read_bytes()==b
  rows.append({'path':str(p),'relative_path':r['path'],'scope':directory,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':r['sha'],'mode':p.stat().st_mode&0o777,'origin_commit':r['origin_commit']})
for name in ['tmp','evidence']: (root/name).mkdir()
report={'schema':'hamon.forge.testpilot-saved-review-source-admission.v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base_commit':packet['base_commit'],'base_tree':packet['base_tree'],'donor_commit':packet['donor_commit'],'baseline_files':23,'combined_files':26,'files':rows,'scope':'Selected package/archive/test/doc closure, not complete repository checkout'}
p=root/'source-admission.json'
with p.open('x',encoding='utf-8') as f:json.dump(report,f,sort_keys=True,indent=2);f.write(chr(10))
b=p.read_bytes();print(json.dumps({'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'baseline':23,'combined':26}))
