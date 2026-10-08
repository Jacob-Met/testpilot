"""Authored read-only input control, using the actual TestPilot API and pytest."""
import datetime
import hashlib
import json
from pathlib import Path
import stat
import sys
import traceback

source, destination = (Path(arg).resolve() for arg in sys.argv[1:])
destination.mkdir()
sys.path.insert(0, str(source))
from testpilot.loop import TestPilot
from testpilot.model import ScriptedModel

repo = destination / 'repo'
(repo / 'tests').mkdir(parents=True)
(repo / 'locked').mkdir()
initial = 'def amount():\n    return 2\n'
(repo / 'values.py').write_text(initial)
(repo / 'locked/alias.py').symlink_to('../values.py')
(repo / 'tests/test_existing.py').write_text('from values import amount\ndef test_existing():\n    assert amount() == 2\n')
(repo / 'locked').chmod(0o555)
diff = '--- a/values.py\n+++ b/values.py\n@@ -1,2 +1,2 @@\n def amount():\n-    return 1\n+    return 2\n'
reply = '```python path=tests/test_generated.py\nfrom values import amount\ndef test_generated():\n    assert amount() == 2\n```\n'
record = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_root': str(source),
          'source_sha256': {str(path.relative_to(source)): hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in [source / 'testpilot/loop.py', source / 'testpilot/sandbox.py']},
          'input_mode_before': oct(stat.S_IMODE((repo / 'locked').stat().st_mode))}
try:
    result = TestPilot(ScriptedModel(['Test amount.', reply]), max_repair_rounds=0, coverage=False).run(
        repo, diff, targets=['locked/alias.py::amount', 'values.py::amount'])
    record['result'] = result.to_dict()
    record['accepted'] = result.status == 'passed' and len(result.changed_functions) == 1
except Exception as error:
    record['accepted'] = False
    record['error_type'] = type(error).__name__
    record['error'] = str(error)
    record['traceback'] = traceback.format_exc()
finally:
    record['input_mode_after'] = oct(stat.S_IMODE((repo / 'locked').stat().st_mode))
    record['caller_source_unchanged'] = (repo / 'values.py').read_text() == initial
    record['caller_link_unchanged'] = (repo / 'locked/alias.py').readlink() == Path('../values.py')
    record['completed_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (destination / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({key: value for key, value in record.items() if key not in ('result', 'traceback')}, indent=2))
