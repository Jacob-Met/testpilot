# Independent TestPilot explicit-target receiving

**Disposition: ACCEPT** source commit `00b63c8e03cc515160da1202331224167d12d253`, tree `d1ba76e3872a0e843821b799f8accb69aa32416d`.

This is the author's 27-leaf scoped composition over canonical `63174afd8e63a0ea562cf188b7d971522f017a30`. It includes the already merged recheck command and unchanged owner sandbox. Root inspected the new resolver and exact CLI/loop/HTML seams, checked the clean source pin, then executed the independent receiver on an existing Python 3.13.7 environment with pytest 9.1.1 and coverage 7.16.2. No dependency was installed.

## Actual receiving

All six independent groups passed, with 23 actual CLI, Git and pytest commands. The command-line default preview was byte-identical to the unchanged e228 preview on the same real Git diff, selecting only the changed `ignored` function. Explicit preview instead selected `Policy.cap` and `accepts` in caller order, deduplicated the repeated method, retained every original requested argument and exact loaded diff, and left both selected unchanged spans' changed-line lists empty.

An actual CLI generation used the unmodified native `ScriptedModel`. A narrow observation wrapper called the real `make_client`, returned its untouched client, and recorded its real outgoing messages; it did not replace model responses or sandbox behavior. The deliberately failing first generated test triggered the real repair loop. Planner, editor and repair messages each contained the exact diff and selected source. Final native execution passed the one existing and two generated tests. This is deterministic workflow receiving, not a claim about live-model generation quality.

The actual exported `testpilot.patch` passed `git apply --check`, applied to a separate fresh Git fixture, and its three-test suite passed through the existing native pytest interpreter. The source and existing test bytes stayed unchanged. Patch SHA256: `9e53e5ac4daa21d8ee93a51c94a60aec14fbee520d48ef683517fc250a456800`.

Ten invalid target cases returned exit 2 before model calls or output-directory creation: missing function, conditional duplicate name, test source, parent traversal, absolute path, outside symlink, non-Python source, syntax error, malformed spec and empty qualified name. The native fixture source and outside file were unchanged. A separate real stdin preview read Latin-1 source using its encoding cookie and Unicode function name, retained exact diff context, and selected a module that would raise immediately if imported; selection did not execute it.

The independent receiver made no candidate-source edits. All candidate package and baseline source fingerprints were unchanged after execution. Temporary synthetic repositories were removed by the receiver; exact fixture definitions, generated patch and native receipts remain in this packet. The receiver completed with exit 0 in 5.89 seconds. Its immediate ordinary-free-space preflight was 2,145,505,280 bytes.

## Evidence and qualifications

- `receive_explicit_targets.py` is the exact independent script, SHA256 `08dc3a0c30cb559e53bc644de966b13dbcafb7bb3c841886963261e28832cf5d`.
- `receiving-result.json` retains all 23 command arguments, output/error streams, exit codes, group assertions, native report and source fingerprints.
- `model-calls/` retains actual client-call observations, including empty refusal observations.
- `native-run/` retains the actual generated report JSON, Markdown, HTML and patch.
- `source-freeze.json` is a byte-identical copy of the author's frozen 27-leaf manifest.
- `source-binding.json` independently binds all 27 current native leaves to the clean received commit and tree.

The author's wider tests and paired parent controls retain their original pins: e228 authored source passed 126 tests plus 18 subtests; two raw-filename fixture failures reproduced before TestPilot invocation on unchanged e228 under macOS. Current631 focused receiving passed 58 tests plus 18 subtests with one existing skip; the existing recheck configured-suite count failure also reproduced on unchanged631. Root did not change or rerun those unrelated owner tests. Those controls qualify the environment and are preserved in the author packet.

The independent default-preview comparison used the untouched e228 import root; the explicit runtime, generation and patch path used the complete current631 composition. This distinction is deliberate and is not a claim of running all historical tests on the new public tree.

## Reproduce

Use a clean source checkout matching the frozen package and an existing supported Python with pytest/coverage. Run the preserved script with explicit `--source`, `--baseline-source` and a new `--out` directory. The original invocation used:

```text
/Users/me/testpilot-html-066deeadcc8b/venv/bin/python receive_explicit_targets.py
  --source /Users/me/hamon-testpilot-explicit-targets-a219f250962c
  --baseline-source /Users/me/hamon-testpilot-target-assessment-a219f250962c/current/snapshot
  --out /Users/me/testpilot-explicit-target-review-a219f250962c/run-01
```

Both `PYTHONDONTWRITEBYTECODE=1` and `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` were set. Replays must use a new output directory and preserve existing receipts. No further behavior rerun is needed for identical source bytes.
