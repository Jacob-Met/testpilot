"""Independent real-process deadline challenge; pass sandbox.py as argv[1]."""
import hashlib
import importlib.util
import json
import os
import platform
import re
import signal
import sys
import tempfile
import time
from pathlib import Path

source = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("receiving_sandbox", source)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
helper = "import os,time\nfor i in range(600):\n os.write(1, ('helper-%04d\\n' % i).encode()); time.sleep(.01)\n"
parent = """import os,pathlib,subprocess,sys,time
child = subprocess.Popen([sys.executable, '-c', sys.argv[2]], start_new_session=True)
pathlib.Path(sys.argv[1]).write_text(str(child.pid))
os.write(1, b'parent-diagnostic\\n')
time.sleep(20)
"""
with tempfile.TemporaryDirectory(prefix="testpilot-streaming-deadline-") as td:
    root = Path(td)
    marker = root / "owned-helper.pid"
    try:
        start = time.monotonic()
        rc, output, timed_out = module._run(
            [sys.executable, "-c", parent, str(marker), helper],
            root, module.clean_env(root), 0.4,
        )
        elapsed = time.monotonic() - start
        numbers = [int(x) for x in re.findall(r"(?m)^helper-(\d+)$", output)]
        continuous = numbers == list(range(len(numbers)))
        survived_until_cleanup = False
        if marker.exists():
            try:
                os.kill(int(marker.read_text()), 0)
                survived_until_cleanup = True
            except ProcessLookupError:
                pass
        result = {
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "timeout_s": 0.4,
            "elapsed_s": elapsed,
            "returned_timeout": timed_out and rc is None,
            "parent_diagnostic_retained": "parent-diagnostic\n" in output,
            "streamed_lines": len(numbers),
            "stream_is_contiguous_without_duplicates": continuous,
            "helper_survived_until_owned_fixture_cleanup": survived_until_cleanup,
            "output_bytes": len(output.encode()),
            "passed": timed_out and rc is None and elapsed < 2.5
                and "parent-diagnostic\n" in output and continuous
                and 40 < len(numbers) < 600 and survived_until_cleanup,
        }
        print(json.dumps(result, indent=2))
        if not result["passed"]:
            raise SystemExit(1)
    finally:
        if marker.exists():
            try:
                os.killpg(int(marker.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass
