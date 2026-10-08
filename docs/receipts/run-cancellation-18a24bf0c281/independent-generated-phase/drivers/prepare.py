#!/usr/bin/env python3
"""Freeze a distinct generated-verification cancellation fixture, without running TestPilot."""
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path('/Users/me/testpilot-independent-interrupt-18a24bf0c281')

WORKER = '''import json
import os
from pathlib import Path
import sys
import time

control = Path(sys.argv[1])
deadline = time.monotonic() + 8.0
identity = {"pid": os.getpid(), "ppid": os.getppid(), "pgid": os.getpgrp()}
(control / "worker-ready.json").write_text(json.dumps(identity))
while time.monotonic() < deadline:
    (control / "heartbeat.json").write_text(json.dumps({**identity, "monotonic": time.monotonic()}))
    flag = control / "parent-exited.json"
    if flag.exists():
        parent_receipt = json.loads(flag.read_text())
        (control / "work-after-parent-exit.json").write_text(json.dumps({**identity, "observed_ppid": os.getppid(), "monotonic": time.monotonic(), "parent_exit": parent_receipt}))
        time.sleep(0.15)
        break
    time.sleep(0.025)
'''

GENERATED = '''import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from pair_math import combine


def test_generated_verification_with_owned_worker():
    assert combine(9, 4) == 13
    control = Path(os.environ["TP_REVIEW_CONTROL"])
    child = subprocess.Popen([sys.executable, str(Path(__file__).parents[1] / "owned_worker.py"), str(control)])
    (control / "generated-ready.json").write_text(json.dumps({"phase": "generated-verification", "pid": os.getpid(), "ppid": os.getppid(), "pgid": os.getpgrp(), "child_pid": child.pid, "generated_path": str(Path(__file__).resolve()), "generated_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "asserted_result": 13}))
    child.wait(timeout=10.0)
'''

def main():
    root = ROOT / 'fixture'
    assert not root.exists()
    (root / 'project/tests').mkdir(parents=True)
    (root / 'script').mkdir()
    (root / 'previous-output').mkdir()
    files = {
        'project/pair_math.py': 'def combine(left, right):\n    return left + right\n',
        'project/tests/test_existing_pair.py': 'from pair_math import combine\n\ndef test_existing_pair():\n    assert combine(6, 7) == 13\n',
        'project/owned_worker.py': WORKER,
        'change.diff': 'diff --git a/pair_math.py b/pair_math.py\n--- a/pair_math.py\n+++ b/pair_math.py\n@@ -1,2 +1,2 @@\n def combine(left, right):\n-    return left\n+    return left + right\n',
        'script/00-plan.txt': 'Check the changed combine function. Generate one additional verification case.\n',
        'script/01-generated.txt': '```python path=tests/test_generated_lifecycle.py\n' + GENERATED + '```\n',
        'previous-output/report.json': '{"fixture":"previous regular report artifact","generation":17}\n',
        'previous-output/report.md': '# Previous regular review artifact\n\nGeneration 17 must survive interruption.\n',
        'previous-output/report.html': '<!doctype html><title>Previous regular review artifact</title><p>Generation 17</p>\n',
        'previous-output/testpilot.patch': '# Previous regular patch artifact, generation 17\n',
    }
    manifest = []
    for name, content in files.items():
        path = root / name
        path.write_text(content)
        data = path.read_bytes()
        manifest.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    expected = {
        'scenario': 'Real SIGINT during generated verification after the actual ScriptedModel planner/editor calls',
        'source_parent': '7f44c4f134f4d56d37dd14c7c2d2aaa3c8c8749e',
        'loop_blob_preserved': 'ed0f5f7f057c217b931a1756bd679ae087247e0a',
        'generated_sha256': hashlib.sha256(GENERATED.encode()).hexdigest(),
        'manual_expectations': [
            'The actual generated test first receives combine(9,4)==13 and writes readiness from its copied source.',
            'The launched pytest leader is in its own process group; its one worker inherits that group.',
            'SIGINT terminates the owning TestPilot CLI within3 seconds and remains an interrupt, not a completed run.',
            'At parent exit the owned pytest group has no running work; zombie states alone are not counted as work.',
            'Only after parent exit does the receiver create its handshake; no worker can then produce a continuation marker.',
            'All four preexisting regular output artifacts retain exact bytes, inode, mode and write timestamp.',
            'Project, scripted replies and all exact production source blobs remain unchanged.',
            'Receiver cleanup is finite and addresses only recorded owned process/group identities; worker lifetime is capped at8 seconds.'
        ],
        'output_contract': 'The four previous-output files are explicitly synthetic regular preservation sentinels. Current CLI accepts an existing output directory and reaches generated verification; no claim is made that these sentinel contents are a prior complete semantic TestPilot report.',
        'network': 'Explicit scripted backend; no external model API or credential is used.',
        'scope_limits': ['POSIX SIGINT during communicate after successful Popen only.', 'No escaped session, SIGTERM/SIGKILL semantics, Windows or hostile-code containment claim.', 'No author suite or uninterrupted-control replay.'],
        'fixture_files': manifest,
    }
    (root / 'expected.json').write_text(json.dumps(expected, indent=2, sort_keys=True) + '\n')
    (ROOT / 'evidence/environment.json').write_text(json.dumps({
        'executable': sys.executable, 'python': sys.version,
        'pytest': importlib.metadata.version('pytest'),
        'coverage_installed': importlib.util.find_spec('coverage') is not None,
        'reuse': 'Explicitly authorized read-only interpreter; all source, fixtures and process/output state are independent.',
        'bytecode_disabled': sys.dont_write_bytecode,
    }, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'fixture_files': len(manifest), 'generated_sha256': expected['generated_sha256'], 'candidate_intake': False, 'testpilot_executed': False}))

if __name__ == '__main__':
    main()
