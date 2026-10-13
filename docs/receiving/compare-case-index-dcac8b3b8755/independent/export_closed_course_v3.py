"""Data-only exact export of one closed owned receiving epoch; never launches a product."""
import argparse,base64,hashlib,json,pathlib
ROOT=pathlib.Path(r'D:\hamon-dcac8b3b8755-testpilot-failure-index-v1')
def ident(p):
 b=p.read_bytes();s=p.stat()
 return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(),'mode':str(s.st_mode),'mtime_ns':str(s.st_mtime_ns),'inode':str(s.st_ino)}
ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['original','candidate']);ap.add_argument('receipt_git');a=ap.parse_args()
course=ROOT/(a.phase+'-course-v3');receipt=course/'receiving.json'
assert ident(receipt)['git_blob']==a.receipt_git
raw=json.loads(receipt.read_bytes());assert raw['passed'] and raw['phase']==a.phase
names=['receiving.json','comparison.html','initial-diagnostics.json','producer.stdout','producer.stderr','before-download.json','after-download.json','diagnostics-390.png','diagnostics-desktop.png']
paths=[course/n for n in names];before={n:ident(p) for n,p in zip(names,paths)}
packet={'schema':'hamon.exact-closed-course-export/1','phase':a.phase,'native_root':str(course),'before':before,'files':[{'path':n,'base64':base64.b64encode(p.read_bytes()).decode()} for n,p in zip(names,paths)]}
packet['after']={n:ident(p) for n,p in zip(names,paths)};assert packet['before']==packet['after']
dest=ROOT/(a.phase+'-course-v3-export.json')
with dest.open('xb') as f:f.write((json.dumps(packet,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps({'path':str(dest),'identity':ident(dest),'members':len(names)}))
