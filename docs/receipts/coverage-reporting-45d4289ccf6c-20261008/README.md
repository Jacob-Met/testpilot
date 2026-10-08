# Configured coverage-report receiving

## Result and source

This contribution fixes TestPilot's coverage measurements when a project uses
Coverage.py's standard `fail_under` setting. It changes the JSON-report
destination/admission in `testpilot/sandbox.py::run_pytest` and one unavailable
message in `testpilot/loop.py::render_report`. The executable-line calculation,
pytest outcome, model loop and timeout cleanup are preserved.

Receiving base: `9f01fcb6de085850eca00db746380795eb548d62`, tree
`34191a66ec22f8630aea83559cfb16f1e464ab3e`.
`base-tree-readback.json` verifies every one of its 294 leaves, including modes,
sizes, Git blobs and SHA-256. Original source remains in that Git ancestry.

| Changed or added path | SHA-256 |
| --- | --- |
| `testpilot/sandbox.py` | `90c1401cba1f5c488f1aa0b89b90293fda41b7971471904381d6b0b8279e18f7` |
| `testpilot/loop.py` | `aa0a7a1459fabe7016e4d4f55fd7ee5fc2a5af64ec9df24445868fcaa59f620b` |
| `tests/test_coverage_reporting.py` | `49c273ba51487a02c8c5b2bccbac1522980bec0f83fad5f854aded868fab7ede` |
| `docs/coverage-reporting.md` | `697fcbf3d7276c0e34ba704b0a611908b0192f4e3c01f554dae3fc8a2bd063dd` |

## Observed defect and corrected outcomes

The actual public CLI used an authored four-statement function, one existing
test and one ScriptedModel-generated test. Coverage.py independently wrote a
valid 75% baseline JSON report with exit 2 under `fail_under=100`.

| Source/configuration | Reported before | Reported after | Reported change |
| --- | ---: | ---: | ---: |
| Original, threshold 100 | 0% | 100% | +100 points |
| Original, threshold 0 | 75% | 100% | +25 points |
| Corrected, threshold 100 | 75% | 100% | +25 points |
| Corrected, threshold 0 | 75% | 100% | +25 points |

Both configurations finish with two passing tests. The ordinary configuration
is an unchanged healthy control. Inputs and source bytes remain exact.

The initial frozen regression file (`initial/test_coverage_reporting.py`)
produced **one pass and five failures** on original source. Root's subsequent
stale-output edge added exactly one case; its separate original-source run
failed. These are **seven unique cases**, with no repeated original six-case run.

The final exact test module plus the existing sandbox and loop modules
produced **28 passed, zero errors/skips**: seven new cases and 21 existing
controls. The dedicated sandbox temporary root was empty afterward.

The added edge uses the actual installed Coverage.py plugin loader. A test
leaves a 93% report at the old fixed path, then configures a plugin that records
its actual `coverage json` invocation and exits 2 before report generation.
Original source reports synthetic zero; the corrected source reports
unavailable. The newly reserved report destination prevents a future exit-2
admission from using that old file. The marker proves this was a real reporting
process exit, not a fabricated command result.

Other cases retain actual zero with its executable population, preserve failed
pytest status alongside readable coverage, and finish the public CLI's JSON,
Markdown and patch outputs when source removal makes final report collection
unavailable. All source removal occurs inside the owned temporary sandbox;
the original project bytes are unchanged.

## Native execution and primary contract

The native receiver used ThinkPad Python **3.14.4**, pytest **9.0.2**, and
Coverage.py **7.16.2**. Existing dependencies were used read-only with bytecode
writes disabled; no environment was installed or modified. The focused
receipt includes hashes of the actual installed Coverage.py `cmdline.py`,
`control.py` and `jsonreport.py`.

Coverage.py's [primary JSON-command documentation](https://coverage.readthedocs.io/en/latest/commands/cmd_json.html)
states that a below-threshold total exits 2 and that configuration files can
supply reporting options (read 2026-10-08). This contribution preserves the
existing TestPilot pass/fail policy; it does not add a coverage-threshold gate.

## Packet and replay

- `source-receipt.json`: ten exact native baseline source/test/config files.
- `candidate-source-receipt.json`, `runtime.patch`, `source-and-tests.patch`:
  complete reviewed delta and pins.
- `baseline/public-cli/` and `candidate/public-cli/`: unchanged executable,
  actual original/corrected CLI outputs, exact authored inputs and raw coverage
  oracle JSON. Native coverage database files are unnecessary for replay and
  are omitted; the original native copy remains retained.
- `baseline/regressions/`, `baseline/stale/`, `candidate/focused/`:
  pytest logs, JUnit, compact native receipts and the stale-report plugin markers.
- `baseline_receiving.py`: accepts an immutable source snapshot and a new output
  directory, then runs both actual CLI configurations and the real coverage oracle.
- `run_receiving.py`: accepts source, new output, and absolute pytest selection
  paths; records source hashes, actual installed versions, outcomes and cleanup.
- `manifest.json`: exact payload inventory; it excludes itself.

The canonical regression module can also run directly:

```bash
python -m pytest -q tests/test_coverage_reporting.py tests/test_sandbox.py tests/test_loop.py
```

These results cover authored local projects and ScriptedModel responses.
Provider/model quality, complete repository/eval coverage, Windows and installed
service adoption are outside this receiving. Existing CI PR #1 and model-timeout
PR #10 remain owned separately. Independent source review and the normal
current-head publication/integration gates follow this native packet.
