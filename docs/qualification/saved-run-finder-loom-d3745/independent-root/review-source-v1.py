"""Read-only source fence and saved-course review, not product execution."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT=Path('/workspace/scratch/d3745ea0f44f')
HERE=ROOT/'root-testpilot-history'
AUTHOR=ROOT/'loom-testpilot-history'

def need(ok, why):
    if not ok: raise ValueError(why)

def identity(path):
    raw=path.read_bytes()
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'git_blob':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}

def load(path): return json.loads(path.read_bytes())

manifest=load(AUTHOR/'candidate-receiving-manifest-v2.json')
need(identity(AUTHOR/'candidate-receiving-manifest-v2.json')['sha256']=='6ed4438395eaca886f69de2b6e6ae65e933a0c96f6a6cded01b01edc3ee1cf89','offered manifest')
freeze=load(AUTHOR/'candidate-freeze-v2.json')
need(identity(AUTHOR/'candidate-freeze-v2.json')['sha256']=='039a16a48e0674e45e67c6b29165bacf1bd494a5d5794c47053cf3641bd20b68','offered freeze')
tree=load(HERE/'base-tree-v1.json')
need(tree['sha']=='6aec92096d7786defc448dc2e5adba838771bcfd' and tree['truncated'] is False,'remote complete original tree')
leaves={x['path']:x for x in tree['tree'] if x['type']!='tree'}
need(len(leaves)==1739,'original leaf count')
candidate=Path(manifest['root'])
old=AUTHOR/'original'
original_files={p.relative_to(old).as_posix():p for p in old.rglob('*') if p.is_file()}
need(len(original_files)==21,'complete original projection')
for name,p in original_files.items():
    need(identity(p)['git_blob']==leaves[name]['sha'],'original remote Git identity: '+name)
    need(format(p.stat().st_mode & 0o777,'o')==leaves[name]['mode'][-3:],'original mode')
changed=[];added=[];same=[]
for row in manifest['files']:
    p=candidate/row['path'];i=identity(p)
    need(i['bytes']==row['bytes'] and i['sha256']==row['sha256'] and p.stat().st_mode & 0o777==row['mode'],'candidate leaf pin')
    if row['path'] not in original_files: added.append(row['path'])
    elif p.read_bytes()!=original_files[row['path']].read_bytes(): changed.append(row['path'])
    else:same.append(row['path'])
need(set(changed)=={'README.md','testpilot/__main__.py'} and set(added)=={'testpilot/history.py','tests/test_history.py','docs/HISTORY.md'} and len(same)==19,'five-file source fence')
cli=(candidate/'testpilot/__main__.py').read_text()
cli=cli.replace('from .history import run_history_command\n','',1)
start=cli.index('    history = sub.add_parser("history",')
end=cli.index('    a = ap.parse_args(argv)',start)
cli=cli[:start]+cli[end:]
cli=cli.replace('    if a.cmd == "history":\n        return run_history_command(a)\n\n','',1)
need(cli.encode()==(old/'testpilot/__main__.py').read_bytes(),'inverse CLI additions')
readme=(candidate/'README.md').read_text()
start=readme.index('## Find saved generation and recheck reports\n')
end=readme.index('## Review your own run in a browser\n',start)
need((readme[:start]+readme[end:]).encode()==(old/'README.md').read_bytes(),'inverse README addition')
v1=(AUTHOR/'candidate/testpilot/history.py').read_bytes()
v2=(candidate/'testpilot/history.py').read_bytes()
need(v1.replace(b'os.fdopen(os.open(path, flags), "rb")',b'os.fdopen(os.open(path, flags), "rb", buffering=0)',1)==v2,'sole versioned raw-read correction')
normal=load(AUTHOR/'author-tests-v1/receipt.json')
optimized=load(AUTHOR/'author-qualification-v1/receipt.json')
correction=load(AUTHOR/'author-read-bound-v2/receipt.json')
need(normal['exit_code']==0 and normal['inputs_before']==normal['inputs_after'],'normal author source custody')
need(optimized['inputs_before']==optimized['inputs_after'] and optimized['original_before']==optimized['original_after'],'optimized/help source custody')
need(all(optimized['checks'].values()) and all(c['exit_code']==0 for c in optimized['commands']),'optimized/help result')
need(correction['exit_code']==0 and all(correction['checks'].values()) and correction['inputs_before']==correction['inputs_after'],'raw-read correction result/custody')
for folder,receipt in [('author-tests-v1',normal),('author-read-bound-v2',correction)]:
    for name,pin in receipt['streams'].items():
        i=identity(AUTHOR/folder/name)
        need(i['bytes']==pin['bytes'] and i['sha256']==pin['sha256'],'author exact stream')
for command in optimized['commands']:
    for stream,pin in command['streams'].items():
        i=identity(AUTHOR/'author-qualification-v1'/(command['label']+'.'+stream))
        need(i['bytes']==pin['bytes'] and i['sha256']==pin['sha256'],'qualification exact stream')
for cmd in ['run','targets','recheck','regression','compare']:
    for stream in ['stdout','stderr']:
        a=AUTHOR/'author-qualification-v1'/('original-'+cmd+'-help.'+stream)
        b=AUTHOR/'author-qualification-v1'/('candidate-'+cmd+'-help.'+stream)
        need(a.read_bytes()==b.read_bytes(),'original subcommand help preserved')
receipt=load(HERE/'received-v1/receipt.json')
need(receipt['accepted'] is True and receipt['cases_passed']==34 and len(receipt['cases'])==34,'independent full result')
spec=load(HERE/'oracles/case-spec-v1.json')
for case,result in zip(spec['cases'],receipt['cases']):
    need(case['name']==result['name'] and all(result['checks'].values()),'actual command membership/flags')
    folder=HERE/'received-v1'/case['name']
    need((folder/'stdout.bin').read_bytes()==Path(case['expected_stdout_path']).read_bytes(),'exact independently authored stdout')
    for stream in ['stdout','stderr']:
        need(identity(folder/(stream+'.bin'))['sha256']==result[stream]['sha256'],'actual stream SHA')
    need(result['returncode']==case['expected_exit'] and not result['timed_out'] and not result['owned_group_cleanup'],'exit and normal closure')
need(all(receipt[k+'_preservation']['unchanged'] for k in ['source','inputs','controls']),'full course preservation')
out={'schema':'hamon.root.testpilot-history.source-and-course-review.v1','created':datetime.datetime.now(datetime.timezone.utc).isoformat(),'accepted':True,
     'source_files':freeze['source_files'],'complete_projection_files':24,'original_projection_files':21,'unchanged_inherited_files':19,
     'original_base':freeze['base_commit'],'original_tree':tree['sha'],'complete_tree_leaves':len(leaves),
     'source_review':'Root read complete history implementation, new21-method test file, complete guide, and exact CLI/README additive diffs after independent controls freeze. Existing21 original Git bodies/modes matched the freshly fetched complete remote tree; inverse additions recover original CLI/README. No executable/provider/model/project-code path is introduced by history dispatch.',
     'author_evidence':'Original v1:21 normal and6 optimized direct methods plus5 byte-identical existing subcommand help pairs; v2:sole buffering=0 correction with4 focused methods and5 observed raw descriptor opens. Saved streams and preservation recomputed without repeating those courses.',
     'independent_evidence':{'commands':34,'passed':34,'receipt':identity(HERE/'received-v1/receipt.json'),'execution_session':58699,'controller_exit':0,'input_namespace_records':22104,'source_namespace_records':34,'control_records':47},
     'limits':'Owned source/control/input observations and real history CLI only; no original record regeneration, native installation, global process/network audit, hostile/concurrent snapshot or whole-suite qualification.'}
with (HERE/'source-review-v1.json').open('xb') as f:f.write((json.dumps(out,indent=2)+'\n').encode())
print(json.dumps({'accepted':True,'source_review':identity(HERE/'source-review-v1.json'),'commands':34,'five_source_fence':True}))
