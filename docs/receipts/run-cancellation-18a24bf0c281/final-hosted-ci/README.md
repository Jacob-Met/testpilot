# Final cancellation receiving and integration

PR43 merged as `6c1c4973f6d88c3cc3d120c76a3b6e30f9008bbb`; issue 35 closed. The actual merge tree `29c33bd4dcd7d6d05d68e87b21530a7f3e69c3d8` equals the tree checked out by successful hosted run [37833468085](https://github.com/Jacob-Met/testpilot/actions/runs/37833468085), job 113504469109. The combined tree preserves all 52 contribution paths and all 1,425 unrelated current-main leaves.

The complete decoded job log records **457 tests and 25 subtests passed** on CPython 3.12.15. Its 16,866 bytes have SHA256 `ee9b7b0e5407aaf3d9f56d6275c15859a36cf370f080c9b8e630e15b6df4f8fc`.

The first hosted run failed two escaped-worker liveness observations. Native diagnosis reproduced pytest's 80-column ps truncation while independently confirming the worker was alive. The correction adds only `-ww` to the test's ps command and a comment. Production cancellation code, assertions, timeouts and cleanup remain unchanged. The original failure, raw diagnosis, failed standalone reproduction controls and corrected native run are preserved under ../ps-width-correction; they are not replaced by this green result.

current-parent-static-review.json preserves the review of the later timeout/diff changes at 513f1745. Its then-pending hosted gate is satisfied by the run recorded here. The original native receiving remains bound to its own source/runtime; this record makes no new native, Windows, deployment or live-provider claim.

This is additive evidence custody rooted at the actual merged commit. qualification.json identifies source, tested checkout, actual merge and limits. tested-merge-tree-proof.json contains complete contribution entries and preservation counts. artifact-manifest.json binds every payload in this directory by byte size, SHA256, Git blob and mode.
