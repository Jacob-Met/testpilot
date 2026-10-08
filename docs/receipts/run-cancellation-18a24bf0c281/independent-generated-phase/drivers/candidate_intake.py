import pathlib,json,hashlib,subprocess,ast,datetime
root=pathlib.Path('/Users/me/testpilot-independent-interrupt-18a24bf0c281')
owner=pathlib.Path('/Users/me/testpilot-cancellation-18a24bf0c281')
commit='649dc7d1fd02493af298876eea0697849404bba9'
manifest=json.loads((owner/'evidence/candidate-source-freeze.json').read_text())
entries=[]
dest=root/'source-candidate'
assert not dest.exists()
for e in manifest['files']:
 blob=subprocess.check_output(['git','rev-parse',commit+':candidate/'+e['path']],cwd=owner,text=True).strip()
 assert blob==e['git_blob']
 b=subprocess.check_output(['git','cat-file','blob',blob],cwd=owner)
 assert hashlib.sha256(b).hexdigest()==e['sha256']
 p=dest/e['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);p.chmod(0o644)
 entries.append({**e,'mode':'100644'})
assert len(entries)==16
base=json.loads((root/'evidence/source-intake.json').read_text())['captured_files']
old={e['path']:e['git_blob'] for e in base};new={e['path']:e['git_blob'] for e in entries}
changed=sorted(p for p in old if new.get(p)!=old[p]);added=sorted(set(new)-set(old))
assert changed==['testpilot/sandbox.py'];assert added==['docs/run-cancellation.md','tests/test_sandbox_interrupt.py']
assert new['testpilot/loop.py']=='ed0f5f7f057c217b931a1756bd679ae087247e0a'
original=(root/'source-baseline/testpilot/sandbox.py').read_text()
candidate=(dest/'testpilot/sandbox.py').read_text()
start=candidate.index('    except KeyboardInterrupt:\n');end=candidate.index('    except subprocess.TimeoutExpired:\n',start)
handler=candidate[start:end]
reconstructed=(candidate[:start]+candidate[end:]).replace('    """Collect output, bounding POSIX timeout and interrupt cleanup."""\n','    """Collect output, with at most one extra second of POSIX timeout cleanup."""\n',1)
assert reconstructed==original
tree=ast.parse(candidate);function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_run')
interrupt=next(n for n in ast.walk(function) if isinstance(n,ast.ExceptHandler) and isinstance(n.type,ast.Name) and n.type.id=='KeyboardInterrupt')
assert isinstance(interrupt.body[-1],ast.Raise) and interrupt.body[-1].exc is None
calls=[ast.unparse(n) for n in ast.walk(interrupt) if isinstance(n,ast.Call)]
assert 'os.killpg(proc.pid, signal.SIGKILL)' in calls
assert 'proc.wait(timeout=1.0)' in calls
assert 'proc.stdout.close()' in calls
intake={'repository':'Jacob-Met/testpilot','canonical_parent':manifest['canonical_parent'],'canonical_tree':manifest['canonical_tree'],'native_candidate_commit':commit,'captured_files':entries,'baseline_receiving_commit':'9317bdb3a0fda248ffcbabbe94c401a4558a1b41','candidate_executed':False,'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(root/'evidence/candidate-intake.json').write_text(json.dumps(intake,indent=2,sort_keys=True)+'\n')
review={'candidate_commit':commit,'old_sandbox_blob':old['testpilot/sandbox.py'],'new_sandbox_blob':new['testpilot/sandbox.py'],'new_sandbox_sha256':hashlib.sha256(candidate.encode()).hexdigest(),'changed_original_paths':changed,'added_paths':added,'unchanged_original_paths':len(old)-len(changed),'retained_loop_blob':new['testpilot/loop.py'],'handler_lines':len(handler.splitlines()),'handler':handler,'inverse_reconstruction_matches_complete_original':True,'original_sha256':hashlib.sha256(original.encode()).hexdigest(),'reconstructed_sha256':hashlib.sha256(reconstructed.encode()).hexdigest(),'inspected_interrupt_calls':calls,'bare_reraise_preserved':True,'bounded_wait_seconds':1.0,'candidate_executed':False}
(root/'evidence/static-candidate-review.json').write_text(json.dumps(review,indent=2,sort_keys=True)+'\n')
print(json.dumps({'candidate_commit':commit,'files':len(entries),'handler_lines':len(handler.splitlines()),'reconstruction_exact':True,'loop_blob':new['testpilot/loop.py'],'candidate_executed':False}))
