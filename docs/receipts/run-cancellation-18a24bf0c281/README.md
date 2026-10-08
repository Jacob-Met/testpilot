# TestPilot cancellation receiving

This repair stops the launched POSIX process group when KeyboardInterrupt interrupts the sandbox's active subprocess communication. It reaps the leader with a bounded wait and propagates the interrupt. The original CLI returned while pytest continued performing fixture work after that return; the candidate stops that work and retains ordinary successful runs.

Tracked scope is [issue #35](https://github.com/Jacob-Met/testpilot/issues/35). Root owns GitHub integration and publication. The source proposal changes only `testpilot/sandbox.py::_run`, adds `tests/test_sandbox_interrupt.py` and `docs/run-cancellation.md`, and carries this additive evidence.

## Source identity

| Role | Exact identity |
| --- | --- |
| Original discovery source, actually executed | main `f3b2135cad31852b599350564fe76dd160a6a522`, tree `d0107a6f8b3b8cc00dadebc5f794060f275f3f5b` |
| Current maintained parent | main `7f44c4f134f4d56d37dd14c7c2d2aaa3c8c8749e`, tree `ea3f7b4170f1515abb7188d31dc269623b9e0738` |
| Original and current sandbox blob | `8ca4a4102c7890e89eae99548e28ba8325974f1e` |
| Frozen candidate native source commit | `649dc7d1fd02493af298876eea0697849404bba9` |
| Candidate sandbox blob | `84330f96ebd71b37dc40575fa2ac59ba53cf2a72` |
| Candidate sandbox SHA256 | `0adf5eb81f8fd15ca09170c5328e6ff4165e1a0f903221b9730de3b480be0b1b` |

The original native source capture has 12 files. The separate current-parent capture has 14: the complete nine-module TestPilot package, its configuration/README/workflow, and two existing sandbox test files. The current canonical tree has 1,063 blobs; these receiving captures are not a full upstream clone. The publication packet is a delta and must be applied while preserving that full parent tree.

Output-staging PR34 changed `loop.py` and README between the original and current captures. The entire sandbox remained byte-identical. Current `loop.py` blob `ed0f5f7f057c217b931a1756bd679ae087247e0a` and every other received current-parent file remain unchanged by this repair.

The production patch adds 15 handler lines and changes its docstring. Removing that handler and restoring the docstring reconstructs the entire original sandbox byte-for-byte, including the existing timeout branch. Candidate freeze records all 16 source/context/test/documentation inputs before execution.

## Native results

All runs below used the existing native Mac environment: macOS 26.6.2 arm64, Python 3.12.8, pytest 9.1.1. No package was installed.

| Receiving gate | Original outcome | Frozen candidate outcome |
| --- | --- | --- |
| Actual CLI, interrupted baseline pytest plus uninterrupted ScriptedModel control | Two CLI actions on f3: three of four predicates pass; pytest performs work released only after its parent exits | Same frozen driver on current7f + repair: four of four predicates pass |
| Focused real-process interruption tests | Four cases on exact current7f: three fail and one detached-session control passes | All four pass |
| Existing sandbox and timeout controls | Preserved source; no duplicate baseline run | Thirteen pass; one existing coverage test skips because coverage is absent |

The candidate combined pytest gate is **17 passed, 1 skipped**, with no test errors. The actual CLI gate independently confirms no interrupted output publication, no post-parent-exit pytest work, successful ordinary execution, and unchanged source bytes. Its interrupted caller exits with -2 in about 0.290 seconds. The ordinary control produces two passing pytest cases and two accepted ScriptedModel entries.

These are four focused pytest cases, fourteen existing pytest cases, and two CLI actions with four predicates; the predicates are not four independent CLI tests.

The focused process observations before fixture cleanup are:

| Fixture | Current baseline | Candidate |
| --- | --- | --- |
| Live leader, same-group child | Leader and child still running; leader not reaped | Both stopped; leader reaped |
| Already-exited leader, same-group child | Leader reaped; child still running | Child stopped; leader remains reaped |
| Live leader, detached child holding stdout | Leader and child still running; leader not reaped | Leader stopped/reaped; detached child still running |
| Already-exited leader, detached child holding stdout | Leader reaped; detached child still running | Same explicit detached-session boundary; caller returns promptly |

The receiver subsequently stops its own detached helpers. New fixtures bind signals to the unique worker script path and recorded process group, provide eight-second worker lifetimes, and have a ten-second fallback cleanup deadline. All completed focused tests verified that their owned fixture processes were no longer running at cleanup completion. The CLI receiver separately records owned pytest-group shutdown.

## Preserved failures and provenance details

The first CLI receiver actually completed both native flows, but aggregate metadata construction read `ledger.calls` instead of the maintained `ledger.entries` field. Its raw KeyError, successful ordinary report, cancellation continuation, and source bytes remain in the raw archive. It is not counted as a clean aggregate run.

The separately frozen v2 receiver corrects that key and exposes input/output/interpreter arguments. Its fixture and cancellation boundary are unchanged. Driver SHA256 is `e80ecd44e02f6bc32c0994bc1665c8ed21c86fa6de266f81a2a0043d0d72b16c`. The original clean negative receipt SHA256 is `2f8ee8748971ac121032f8db75746bd89e523c48fecf3815e4aa1329c13d98b8`.

The unchanged v2 driver's raw receipt contains historical hardcoded f3 head/tree labels. For the candidate run, **candidate-cli-composition.json is the authoritative current7f + repair binding**, with all actual source hashes. The raw candidate receipt is retained without rewriting those historical fields; it is not evidence that f3 was executed again.

The current-parent focused tests were frozen before the repair at `d017324348fba8035646b77426aa3b94497d6d89`, SHA256 `466bbdd470001a5e23e55a1205352dfccc8c714470fe903ff241b28416449325`. Their three failures and passing control were retained at `fe6adc337ada4421a1e978d58998eec3e8478d43` before the production source freeze.

## Artifacts and review boundaries

- `candidate-source-freeze.json`, `current-parent-source.json`, and `qualification.json` bind the source, environment, commands, outcomes, and ownership scope.
- `original-cli-receipt.json`, `current-focused-receipt.json`, `candidate-pytest-receipt.json`, and `candidate-cli-composition.json` preserve the separate stages.
- `production.patch` is the complete production-code delta.
- `receive-cancellation.py` is the unchanged real CLI receiver. The focused regression tests are published in the ordinary tests directory.
- `raw-native.tar.gz` contains every retained original/current/candidate input, raw gate output, fixture and receipt selected by `raw-manifest.json`. Every regular archive member is reopened and byte-verified. Pytest convenience symlinks are retained as target metadata in that manifest rather than emitted as absolute archive links.

The native signal receiving is scoped to KeyboardInterrupt during the sandbox's initial communication on POSIX. It does not qualify SIGTERM/SIGKILL handling, pre-Popen interruption, Windows behavior, escaped-session containment, optimized-Python execution, or the whole repository suite. Cleanup remains bounded if the OS refuses a signal or the leader cannot be reaped promptly; the original interrupt propagates. The sandbox remains process-level isolation. No live provider, developer repository, deployment, goal, service or other owner's source was used.

The existing timeout and normal-result contracts remain unchanged. An interrupted attempt does not reach the CLI's normal publication step; earlier test effects or model calls are not rolled back.
