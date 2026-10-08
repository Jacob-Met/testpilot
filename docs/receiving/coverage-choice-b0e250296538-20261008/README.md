# Native CLI coverage choice — qualified author receiving

This contribution exposes the existing Python API's coverage=False behavior as `testpilot run --no-coverage`. Omission keeps automatic measurement when the selected Python has coverage installed. The native runner, sandbox, selector, model, report writer, patch format and actual test-result classification are inherited unchanged.

Source lane: estate-b0e250296538 / live_coordination. Coordination is [TestPilot #36](https://github.com/Jacob-Met/testpilot/issues/36), with the active explicit-target owner notified on [#30](https://github.com/Jacob-Met/testpilot/issues/30#issuecomment-6062751850). Root retains independent source acceptance and final integration. Saved-run comparison and explicit-target work remain their original owners' scopes.

## Exact source

The received current parent is `7f44c4f134f4d56d37dd14c7c2d2aaa3c8c8749e`, tree `ea3f7b4170f1515abb7188d31dc269623b9e0738` (1,063 leaves). The only product-code edits are a run parser argument and forwarding its default-None/explicit-False value to the existing TestPilot constructor. The README receives one paragraph and the repository receives six real CLI regression cases in a new test module.

The CLI candidate is blob `65b7274680c22dfbf00e3274d01757d52c8eb55c`, SHA-256 `3097ddba2b7ef0381ca31cb2ef20852b6541b70384da0bd137da018f35a966c1`. Removing the two exact insertions reconstructs the parent CLI byte for byte. The current output-staging writer is inherited blob `ed0f5f7f057c217b931a1756bd679ae087247e0a`; it is not this contribution's implementation.

The [current source manifest](source-current.json) distinguishes the 16 materialized runtime/configuration/test files from the complete authoritative repository tree. Native execution is a bounded source selection, not a full checkout.

## Original observations

The [separate macOS baseline receiver](receive_baseline_macos.py) authors Git fixtures with ordinary filenames and an optional coverage plugin that deliberately fails during its own initialization. The source is frozen main `f3b2135cad31852b599350564fe76dd160a6a522`.

| Actual original route | Native result |
| --- | --- |
| Default CLI, failing optional plugin | Exit 1; coverage initialization fails before pytest results |
| Unchanged API with coverage=False, same fixture | Exit 0; existing and generated tests both pass |
| Current CLI with --no-coverage | Exit 2; parser rejects the missing option |
| Default CLI, ordinary fixture | Exit 0; both tests pass with real measured coverage |

All four project inputs and all original runtime source bytes remain unchanged. [The original summary](evidence/baseline-summary.json), exact command receipts and driver logs retain these observations. This capability does not turn instrumentation failure into a passing test result; a user explicitly chooses an existing uninstrumented execution path.

## Actual candidate gates

On the first frozen source composition, all six new cases passed in 5.25 seconds. They execute eight public run commands, covering automatic/disabled measurement, the optional-plugin failure boundary, a genuinely failing generated assertion, baseline/generation/repair, and a selected project interpreter whose dependency is absent from the tool environment.

Current main then received the unrelated output-staging change. We copied that exact writer and README into a new immutable source composition and tested the changed output path together with existing CLI/interpreter, targets, coverage-reporting and saved-test recheck cases. The actual current gate reports **62 passed, one skipped and six subtests passed in 19.90 seconds**. The gate receipt records the skip reason and exact command. Every one of the 16 staged files remained unchanged. This is the declared native subset; the repository's full hosted workflow is a separate publication/integration gate.

Runtime: macOS 26.6.2 arm64, Python 3.12.8, pytest 9.0.2, coverage 7.16.2. A private pinned tooling environment was prepared under this contribution directory after availability and capacity checks. Only authored disposable projects were executed; no provider credentials or external model call were used.

## Receiving limits and retained setup evidence

An earlier, separately named ThinkPad probe was submitted through RDC, but its start and subsequent receipt reads timed out without returning a PID or execution receipt. Its outcome remains unknown and it was not replayed or credited as a result. The Mac filesystem preflight refuses an invalid UTF-8 filename with EILSEQ (92), so the Mac receiver deliberately uses an independently authored ordinary-path instrumentation fixture. These are distinct transport/filesystem observations, not product test failures.

The first in-memory test-authoring carrier was rejected by JavaScript parsing because of a fixture Markdown fence; no tool call, file write or test execution occurred. The corrected carrier uses chr(96) to author that fixture text.

The complete native archive preserves the source manifests, authored input/command/result evidence, both native candidate gates and setup receipts. Reproducible tooling binaries and virtual environments are excluded. The compact repository packet keeps the consequential raw receipts and source pins. Source publication and integration receipts bind the final Git tree separately; neither a green hosted run nor a merge is inferred here.
