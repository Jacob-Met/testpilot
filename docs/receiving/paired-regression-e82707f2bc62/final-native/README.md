# Paired Git-revision regression — integrated native receipt

The new `testpilot regression` CLI and `check_regression` API execute the same admitted retained tests against two explicit immutable local Git revisions. A verified result requires matching generated case identities and at least one actual failed-before/passed-after witness; existing-suite failures, skips, missing collection and identity drift cannot substitute for that witness. Both trees and test placements are admitted before execution, and the caller’s checkout and prior output remain untouched.

PR #51 merged at `906ce149fba770a62c9f5f2fbc1b7238b949d423` on 2026-10-08 at 20:36:18Z; issue #44 closed one second later. The actual merge tree is `626557015edc297dfc6ba00028a8de64f7dfdfa9`, with ordered parents `e114902b4c938dbf701f30a8299460a86a32dc0a` and `30c56b1c738f5d2b29ce0c9cc36e43754f4c6921`. Complete readback preserves 1,485 unrelated current-parent leaves plus 14 owned paths, with 12 additions and no deletions. Shared CLI/README edits reverse exactly to the current selector parent.

| Actual execution | Result | Exact checkout/tree |
| --- | --- | --- |
| [First native CI](https://github.com/Jacob-Met/testpilot/actions/runs/37832714318) | 473 passed, 25 subtests; 124.86s |`cdb610aea375f8ff9a9620fe0ad3333afd602788` / `de42bf17881ef20895940cf5a7d301fa1e5e91c7` |
| [Cancellation composition CI](https://github.com/Jacob-Met/testpilot/actions/runs/37836353351) | 477 passed,25 subtests; 104.89s |`1957012ae25328b120b32766c565a742e025543f` / `036cf365e5b59c8cdd6edd203b599abb9bc12c7b` |

Both genuine hosted runs used pytest 9.1.1 and coverage 7.16.2 and reported no failures, errors or skips. The early synthetic metadata `6128004e` was not the executed checkout. The later selector PR reached main during the merge guard; its generation-only loop/HTML changes and disjoint CLI/README additions were qualified by exact source and full-tree comparison. The paired sandbox and saved-test admission remained unchanged. The 477-test run is not relabeled as an execution of that later selector composition.

The two gzip files preserve complete decoded native logs byte-for-byte. `receiving.json` records their exact UTF-8 byte counts and hashes, independent receiving, source pins, original failure boundaries, final merge readback and scope release. `selector-composition-proof.json` records the independent predicted tree and additive inverse. Original producer/peer controls, raw results, harness correction and capacity failures remain in the integrated parent evidence archives; no previous failure was rewritten as a pass.

This branch adds receiving evidence only over the actual integration commit. It does not change any product, test or workflow file. No live provider or customer project was used, and no new network/OS isolation claim is made.
