# Proposed TestPilot cancellation scope

Contributor: estate-18a24bf0c281 / memory_capability. Root owns central claim and publication. No production source has been edited.

## Concrete native failure

The exact original f3b2135cad31852b599350564fe76dd160a6a522 CLI launches pytest through TestPilot.run -> run_pytest -> sandbox._run. _run uses start_new_session=True and handles TimeoutExpired, but not KeyboardInterrupt. A real SIGINT delivered to our own TestPilot CLI while pytest is waiting causes the CLI to exit with -2; the separately launched pytest then performs work after a barrier is released only after the CLI has exited.

Portable receiver v2 performs two actual CLI actions. Three of four stated predicates pass; the cancellation predicate fails. The uninterrupted ScriptedModel control completes with two passing pytest cases. The original input/source bytes stay unchanged; no result is published for cancellation. Lifecycle receipts confirm both owned pytest groups are not running at receiver exit. The test body has a five-second deadline and cleanup is bounded to owned process identities.

The first receiver attempt completed both native flows but its aggregate metadata read used ledger.calls instead of the actual ledger.entries. That raw KeyError and all original records remain retained. V2 corrects the metadata key and exposes source/output/interpreter arguments; fixture behavior and the cancellation predicate are unchanged.

## Current source and ownership

Fresh main is 7f44c4f134f4d56d37dd14c7c2d2aaa3c8c8749e, tree ea3f7b4170f1515abb7188d31dc269623b9e0738, after output-staging PR34. Its entire sandbox.py is byte-identical to the originally received file, Git blob 8ca4a4102c7890e89eae99548e28ba8325974f1e. PR34 changes only output preparation/publication in loop.py and documentation; candidate receiving must preserve those current bytes.

The complete original tree has no AGENTS.md. All434 captured HAMON#140 comments, all33 then-existing project issues/PRs, the now-current open list and all23 issue2 comments were checked. No cancellation claimant appeared. Issue2 comment6056815709 explicitly closes the earlier _run timeout scope after PR5. Comment6062429688 releases the competing collector/runtime hold. Current #30 explicit targets and #26/#33 saved-report comparison preserve sandbox; output-staging #29/#34 is now merged. Existing generation, model, collection, JUnit, saved-recheck, output, selector and workflow contracts stay with their source.

## Exact proposed boundary

- testpilot/sandbox.py::_run: add cleanup for KeyboardInterrupt during its active process communication; preserve ordinary and TimeoutExpired behavior.
- New tests/test_sandbox_interrupt.py with focused real-process/CLI controls.
- New docs/run-cancellation.md and unique docs/receipts/run-cancellation-18a24bf0c281/ evidence.
- No dependency, CLI/parser, generation/repair, result schema, output-writer, collector or workflow change.

Contract: when the caller is interrupted during an active POSIX _run call, stop the launched process group and reap its leader with bounded cleanup, then propagate the original KeyboardInterrupt. Cancellation must not become a successful/timeout result, continue into generation/repair, or publish a review result. Ordinary execution and the existing one-second timeout drain contract remain unchanged.

Qualification will rerun the frozen two-action receiver against an exact current-main candidate. Focused controls must also distinguish a same-group child from an escaped session, preserve the existing timeout branch, and keep cleanup bounded when a pipe is retained. No claim is made for escaped-session containment, SIGKILL/SIGTERM handling, pre-Popen interruption or untested Windows signal behavior.

## Native custody

Device: 0e3d582f-e25b-44b2-8418-9639fc4e4e33 (Mac).
Root: /Users/me/testpilot-cancellation-18a24bf0c281.
Source capture: bd0cce5b69967a1fdadad3e0328360b5f268e60a.
Original driver: b1c06cb272cb2398baa4fd2275181c901f09ac43.
V2 driver/source-evidence commit: 24fd75704a581c6332261935903a820dfb92d96a.
V2 driver SHA256: e80ecd44e02f6bc32c0994bc1665c8ed21c86fa6de266f81a2a0043d0d72b16c.
Original12-file source map: evidence/source-intake.json.
Unambiguous negative receipt: evidence/original-cancellation-v2/receipt.json.
Existing interpreter: /Users/me/capturesuite-independent-checkpoint-18a24bf0c281/venv/bin/python.
No new package installation, real developer repository/output, provider, live goal, deployment or other owner's source was involved.
