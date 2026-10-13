# Receive TestPilot on a published fanout regression

This example runs TestPilot's existing `regression` command on two immutable fanout revisions with three retained, authored tests. It preserves the complete before-and-after reports and checks their actual test identities, outcomes and source pins. It uses the existing native pytest runner and makes no model request.

## The concrete consumer

| Input | Exact source |
| --- | --- |
| TestPilot | `b751e1cff2b7902bbebd6e7040f764d49bcb1a46` |
| Fanout before | `0317b4bc80638a8e952857aa5966b0e20d1fab72` |
| Fanout after | `522c40bd3f40359d598b62cf2947d74b14c20a31`, the existing [PR15 owner's source](https://github.com/Jacob-Met/multi-agent-fanout-engine/pull/15) |
| Retained test bytes | SHA-256 `dd35698b41ae63f6d2117849e301bb04fcd3673afae18974160c960d2cb9e3b2` |

The fanout production change replaces a repeated project-wide queued lookup with the existing indexed per-part lookup. The selected retained witness checks a specific resulting error contract: if a ready part's durable row is missing, dispatch must raise the existing `LedgerError` before submission. The old source silently skips the missing part; the indexed source surfaces the error. This course does not measure dispatch performance or establish which behavior was intended before that source change.

The other two retained methods check callback-mutated eligibility and the transactional admission guard. Their bytes come unchanged from the independently reviewed [fanout reference](https://github.com/Jacob-Met/multi-agent-fanout-engine/blob/36f51a846353fa9ab1fb367fdcf0392fe38d325c/tests/test_dispatch_eligibility.py). The accepted implementation belongs to PR15. The overlapping reference PR21 was closed without merge.

`retained-tests.json` is explicitly labeled `authored_receiving_fixture`. It is an admitted retained-test input for the maintained reader, not a model-generation report. Its test path is `tests/test_retained_dispatch_3163ad952d45.py`, absent from both target trees, so the after revision's own `tests/test_dispatch_eligibility.py` remains intact.

## Run from existing source

Use Python 3.12 or newer with pytest already installed and an installed Git that supports `--no-lazy-fetch`. The receiving wrapper installs and fetches nothing. Select an existing TestPilot source directory whose 18 runtime, configuration, license and command-guide leaves match `testpilot-source.json`, and an existing fanout Git worktree that already contains both full commit identities. The source directory can be a normal checkout or the exact selected-source directory in the receiving packet.

Keep `receive.py`, `retained-tests.json`, `expected-inputs.json` and `testpilot-source.json` together. Replace these absolute example paths with your reviewed local locations; the output parent must exist and the output itself must be new.

```sh
testpilot_receiving_tools='/absolute/path/to/docs/receiving/fanout-regression-3163ad952d45'
testpilot_selected_source='/absolute/path/to/pinned-testpilot-source'
fanout_selected_checkout='/absolute/path/to/multi-agent-fanout-engine'
testpilot_receiving_output='/absolute/path/to/new-fanout-regression-result'

python3 -B "$testpilot_receiving_tools/receive.py" \
  --testpilot-source "$testpilot_selected_source" \
  --fanout "$fanout_selected_checkout" \
  --python /absolute/path/to/python3 \
  --output "$testpilot_receiving_output"
```

The wrapper invokes the maintained `python -B -m testpilot regression` entry point with the full before/after refs, the exact retained input, a 60-second limit for each pytest phase and a fresh output directory. It gives the complete command a 150-second outer deadline. Temporary source snapshots stay under the new receiving output's `tmp/` directory. It disables unrelated pytest plugin autoload, Python user-site loading and bytecode writing, removes inherited `PYTHONOPTIMIZE`, and records those settings. This is a controlled local project execution, not an operating-system or network isolation boundary.

The separately preserved native packet contains a transport derived from a checkout that was shallow at the before commit. Its `transport.json` explains the original shallow boundary and exact import procedure. Ordinary cloning of that bundle alone fails Git's missing-parent connectivity check. The verified import declares the original shallow boundary before unbundling and checking out the selected after commit. This preserves the original commit and complete selected-tree bytes; it does not claim pre-boundary history. A normal existing checkout with both refs does not need that transport procedure.

## Acceptance and evidence

The wrapper accepts only when all of these observations hold:

- The actual command returns `verified_regression` and reports zero model calls.
- The before/after commit, tree, complete source inventory hash and retained input bytes match the frozen identities.
- Every maintained test identity has its expected passing result: 69 methods before and 73 after. The additional three retained identities are present in both runs with no duplicate, missing, skipped or error cases.
- The retained missing-row method is the single failed-before/passed-after witness. The other two retained methods pass in both runs. The complete after suite passes, with valid JUnit evidence and no timeout.
- TestPilot source, the retained input, and the fanout worktree and index remain unchanged.

`receipt.json` contains `accepted: true` only for the complete course. The raw maintained reports remain in `command-result/regression.json` and `command-result/regression.md`; the JSON retains every native case and both full native result counts. `command.stdout`, `command.stderr` and `operation.json` preserve the outer process observation. A timeout retains partial binary output and has a null process exit code. A missing report or a nonaccepting result is retained and fails the wrapper.

The three retained methods and the complete maintained-suite counts are separate checks. TestPilot's `exact_files=True` preserves the retained bytes; it does not restrict pytest collection to those files. Source and execution qualifications apply only to these pinned inputs and the recorded interpreter/pytest environment. They do not qualify model generation, provider integration, current main, or unrelated TestPilot behavior.

## Completed native receiving

The frozen receiver passed all 17 checks in one actual ThinkPad course using Python 3.14.4, pytest 9.0.2 and Git 2.53.0. TestPilot returned `verified_regression` with the single expected missing-row witness and reported zero model calls.

| Result | Before | After |
| --- | --- | --- |
| Maintained methods | 69 passed | 73 passed |
| Retained authored methods | 2 passed, 1 failed | 3 passed |
| Complete JUnit cases | 72 | 76 |
| Complete case outcomes | 71 passed, 1 failed | 76 passed |
| Additional pytest subtest output | 164 passed | 164 passed |

The failing before method reports `AssertionError: LedgerError not raised`. The full after suite, including the owner's four added maintained methods, passed. Source, fixture, worktree and index preservation checks all passed. A second worker independently re-derived the maintained identities from the original Git objects and compared every recorded case and outcome with the complete native report.

`QUALIFICATION.json` records the exact source, result and archive identities. The 493,079-byte native evidence archive has SHA-256 `91bb6320c6917d7037e583fc2ccc676e906efb9e8d2a2d2da2c94e396c6814e1`; it preserves the complete command report, exact inputs and import/process records. The 164 subtests are separate native pytest output, not additional JUnit cases or additional retained methods. Prepared expectations and source review remain distinct from this completed execution.
