# TestPilot: qualified isolated ThinkPad review installation

Source: f27ad21fa1f130e74defdda4403028d3ed11806e
Wheel SHA256: cdb743f38fc17fd4caee4f3d0d98761cf8495f8992e2cbb5703444674578f54d
Wheel version: 0.1.0 (the hash and source commit distinguish this review build).

This installation is owned by team7cb7e049e2c0/runtime-consumer:
  /home/jacob/TestPilot-receiving-7cb7e049e2c0/venv
Device: hamon-thinkpad (cadafaf3-4d0b-4c4f-a0d3-34a95d2cec90), jacob uid1000.
Python3.14.4; pytest9.0.2 is reused read-only from the existing system environment.
No dependency downloads or existing project/global package changes were made.

Use the installed command directly:
  /home/jacob/TestPilot-receiving-7cb7e049e2c0/venv/bin/testpilot --version
  /home/jacob/TestPilot-receiving-7cb7e049e2c0/venv/bin/python -I -m testpilot run --help

The completed fixed-response example is under course-v1:
- generated/report.html and report.json: actual generation and one repaired test.
- generated/testpilot.patch: the received saved patch.
- recheck/recheck.html and recheck.json: three passing tests, zero model calls.
- receiving.json: exact module identities, bounded-output and unchanged-input checks.

For another safe fictional example, select a NEW output directory and run:
  /home/jacob/TestPilot-receiving-7cb7e049e2c0/venv/bin/python -I -B receive_installed_toolkit.py --source /home/jacob/TestPilot-receiving-7cb7e049e2c0/venv/lib/python3.14/site-packages --out /home/jacob/TestPilot-receiving-7cb7e049e2c0/new-owned-example

Run that command from this receiver directory. The example creates its own files,
uses fixed model responses, adopts a patch only in its own fresh Git fixture,
and emits16MiB of bounded test diagnostics per execution. It needs no model account.

native_receiving-v2.json is the final native acceptance. native_receiving.json and
receive_native_wheel_v1.py retain an initial harness-only failure: the receiver
expected a bare version, while the correct output is "testpilot 0.1.0".
The existing successfully installed environment was reused; there was no reinstall.

This is a qualified isolated review installation, not a package-index release or a
replacement of another owner's application. Coverage is absent and not claimed.
No live provider, Windows, hardware or GitHub Actions result is implied.
