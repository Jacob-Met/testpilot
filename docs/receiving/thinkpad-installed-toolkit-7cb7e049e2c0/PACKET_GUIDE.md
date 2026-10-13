# TestPilot: installed ThinkPad receiving supplement

A new isolated TestPilot review installation is ready on hamon-thinkpad. The installed command completed an actual fixed-response generation → repair → saved Git patch → adoption → recheck course.

## Use the native installation

Device: hamon-thinkpad, Remote Desktop Commander ID cadafaf3-4d0b-4c4f-a0d3-34a95d2cec90, jacob uid1000.

Native directory: /home/jacob/TestPilot-receiving-7cb7e049e2c0
Interpreter: /home/jacob/TestPilot-receiving-7cb7e049e2c0/venv/bin/python
Console: /home/jacob/TestPilot-receiving-7cb7e049e2c0/venv/bin/testpilot

Run either command on that device:
```sh
/home/jacob/TestPilot-receiving-7cb7e049e2c0/venv/bin/testpilot --version
/home/jacob/TestPilot-receiving-7cb7e049e2c0/venv/bin/python -I -m testpilot run --help
```

The correct version output is "testpilot 0.1.0". The unchanged version number is a review build; use its wheel hash and source pin to distinguish it.

For another fictional, fixed-response course, choose a NEW output directory:
```sh
/home/jacob/TestPilot-receiving-7cb7e049e2c0/venv/bin/python -I -B /home/jacob/TestPilot-receiving-7cb7e049e2c0/receive_installed_toolkit.py --source /home/jacob/TestPilot-receiving-7cb7e049e2c0/venv/lib/python3.14/site-packages --out /home/jacob/TestPilot-receiving-7cb7e049e2c0/new-owned-example
```

This creates its own fictional project, uses fixed model responses, emits 16 MiB of diagnostics per existing-test execution, and applies a saved patch only in its own fresh Git fixture. No provider account is needed. Existing files in that chosen output path cause refusal.

## Exact source and original installable kit

Product commit: [f27ad21fa1f130e74defdda4403028d3ed11806e](https://github.com/Jacob-Met/TestPilot/commit/f27ad21fa1f130e74defdda4403028d3ed11806e).
Source tree: 8e1038af7288d1a85f87b666b4b9b4ed774a7179.
The separate prior receiving-documentation commit is a105ed31b8240667174e7cd3dc74779d087955b5; it does not change this installed product.

[Original immutable installable wheel kit](https://drive.google.com/file/d/1y40JUT9HPjl1UGEqdE27tBKxtNrd_LBe/view).
Wheel: testpilot-0.1.0-py3-none-any.whl, 78,834 bytes, SHA256 cdb743f38fc17fd4caee4f3d0d98761cf8495f8992e2cbb5703444674578f54d.
The wheel remains in that kit; this supplement contains exact native evidence rather than another wheel copy.

## Observed result

The native Python 3.14.4 environment reuses existing system pytest 9.0.2 read-only through a new venv with system-site-packages. pip came from bundled ensurepip. Installation used --no-index --no-deps --no-compile; there were no dependency downloads or changes to global packages or another owner's project.

All 16 installed Python module hashes match the wheel and exact published source, before and after the consumer course and at collection. Both module and console version entrypoints passed. The actual consumer used isolated Python invocation (-I, no PYTHONPATH), native pytest, and Git:

- Generated one initially failing test, then repaired it in one round.
- Final run: 3 passed, 0 failed/errors/skipped, including a legacy test despite an unrelated ancestor testpaths setting.
- Preserved the final diagnostic while retaining a 3,000-character tail of 16 MiB test output.
- Checked and applied the actual saved patch in a new owned Git fixture.
- Recheck: 3 passed, generated test already present, 0 model calls.
- Original project and adopted pre-existing files remained unchanged.
- Native acceptance completed 2026-10-13T10:49:36.417720Z.

The first native receiving script mistakenly expected bare "0.1.0". Installation and source checks had already succeeded; the actual correct output was "testpilot 0.1.0". Both failed receipt and script are retained. The continuation reused the same installed environment, corrected only that assertion, and completed successfully. There was no reinstall or product correction.

## Open the evidence

After extracting, open evidence/native/course-v1/generated/report.html and evidence/native/course-v1/recheck/recheck.html. The corresponding JSON, Markdown, saved patch, fixture source, fixed responses and command logs are beside them. On the ThinkPad these are under the native directory's course-v1.

The frozen unchanged reusable consumer's receipt contains its inherited "Local POSIX consumer receiving; no installed-estate or Windows claim" qualification. This supplement separately establishes this one actual isolated ThinkPad installation; it does not broaden that statement into estate-wide/default deployment.

## Verify this supplement

With only Python's standard library:
```sh
python verify_packet.py
python verify_packet.py /path/to/this-packet.zip
```

Verification checks every payload, nested native manifest, source/module identities, both final reports, bounded output and retained test fingerprints, original-input preservation receipts, and the initial assertion history. It does not rerun tests. Optionally pass --wheel /path/to/testpilot-0.1.0-py3-none-any.whl to verify the external original wheel against all 16 installed module pins.

The native installation runners are historical evidence and require their original transfer payload; they are not portable replay commands. Use the unchanged receive_installed_toolkit.py entry point above for a fresh owned course.

## Limits

This is a qualified isolated review installation. Existing system pytest is reused; it is not an independently resolved clean dependency environment. No coverage package, live provider, Windows, hardware, GitHub Actions, package-index release or replacement of a default estate application is claimed. A future interpreter or dependency change requires receiving again.
