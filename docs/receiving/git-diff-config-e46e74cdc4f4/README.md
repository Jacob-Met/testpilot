# Stable Git input for target discovery

This contribution keeps TestPilot's Git-based target selection bound to the actual changed Python source. On parent 191cca4e416286a9e1fa4b5d5daf5fc30b936db6, ordinary Git color and prefix preferences can hide real changes. With diff.noprefix and an authored same-line decoy, the original CLI selects subject.py::decoy instead of the changed a/subject.py::answer. Configured external diff and text-conversion helpers can also replace the source patch.

## Source change

Only the Git argv in testpilot/__main__.py::_read_diff changes: --no-ext-diff, --no-textconv, --no-color, --src-prefix=a/ and --dst-prefix=b/. The base revision, Python pathspec, subprocess error handling, raw-file/stdin branches, decoding and target parser retain their behavior. A short README note documents the Git input contract. A new real-Git CLI test module checks the behavior through preview and actual scripted generation.

Independent static review restores the complete original runtime AST by removing exactly those five literal arguments. Removing the one README note restores its exact parent bytes. The other 1,177 tracked parent leaves and every original mode are preserved. Final source and test hashes are in manifest.json and review/review-final.json.

## Native receiving

All execution here is on native ThinkPad Linux, Python 3.14.4 and Git 2.53.0, with synthetic project fixtures and no model-provider requests.

- The same final authored test file runs against the exact parent in a separate detached worktree and against the candidate: five methods produce eight baseline failures, then all five methods pass. The scripted generation case checks the intended changed function, planner/editor ledger, exact generated test, two passing pytest tests including one generated test, applicable patch, and unchanged source/index/config.
- The independent receiver freezes its contract before candidate access and uses a same-line decoy and module-execution sentinels. Original source passes four of twelve cases; the candidate passes all twelve. The positive direct-Git controls actually execute configured helpers, while the candidate CLI does not. Raw file/stdin input retains exact parity and an invalid Git reference still returns a real error.
- Existing CLI diff-transport, targets and explicit-target tests pass: 25 tests and 18 subtests. This includes the existing encoding/transport and selection contracts.
- Source review found that the first version of the new authored fixture inherited Git repository-routing variables. Private sentinel controls reproduced an out-of-fixture COMMIT_EDITMSG change and an index change. The final fixture removes inherited GIT_* before its first Git command. Both corrected controls create their own repository and preserve every sentinel file byte, including .git.

The fixture problem belongs to the new regression test and was corrected before source publication. It does not broaden the runtime change.

## Reproduce the behavioral comparison

Use a normal local checkout of this candidate and an isolated detached worktree at the exact parent. Keep output directories outside either source tree. Python must satisfy the project's version requirement and have its normal pytest dependency available.

    git worktree add --detach /tmp/testpilot-original-RECEIVER 191cca4e416286a9e1fa4b5d5daf5fc30b936db6
    bash docs/receiving/git-diff-config-e46e74cdc4f4/receive-final-authored.sh /tmp/testpilot-original-RECEIVER "$PWD" /tmp/testpilot-authored-RECEIVER

The receiving wrapper pins the final test and candidate runtime hashes, checks the original source HEAD and requires baseline exit 1 and candidate exit 0. Inspect the baseline log for its eight expected failures. The original run records 16.309 seconds and the candidate 8.391 seconds; these are observations from this execution, not performance claims.

For independent receiving, run the unchanged independent/receive.py with --source pointing first to the original worktree and then to this candidate, using two distinct absent --out directories outside both checkouts. Its frozen contract.json must remain beside the method. The baseline is expected to fail eight cases; the candidate must pass twelve.

The fixture-isolation receiver and static-review finalizer are retained exactly as executed, including their original native paths. Their original/corrected receipts, full child output and frozen test snapshots are preserved. They are historical methods; a replay must explicitly choose fresh private receiving directories and source locations rather than overwrite the recorded run.

## Preserved negative evidence and custody

The author/original-config-method.py.txt and original-helper-method.py.txt are exact discovery methods from before the source edit. They name the then-current checkout directly; do not run them against a modified checkout and call that an original-source result. Their recorded baseline hashes and raw output establish the historical run. The final receiving wrapper above is the pinned original/candidate comparison.

Earlier authored logs are retained. An early unreachable report-key assertion was corrected before the frozen original/candidate runs. The first final direct script launch lacked PYTHONPATH and failed import before any test ran; that launch failure is preserved separately. The corrected invocation uses an explicit source root. The initially examined diff.outputIndicatorNew setting did not alter the fixture's output and is retained as negative evidence, not listed as a repaired defect.

The independent raw CLI stdout/stderr hashes are checked against each case receipt during packaging. The scoped .gitattributes keeps evidence bytes exact and permits intentional trailing spaces in retained .log and .diff transcripts. The first staging whitespace check identified unittest progress-line spaces and unified-diff context lines; these raw observations are preserved rather than rewritten. manifest.json lists every evidence file except itself plus the three product/source hashes. Native coordination inventories and unrelated estate records remain in the existing estate continuity system rather than this public source packet.

At sealing, this is a locally implemented and independently received source contribution. The subsequent GitHub PR, hosted checks and integration receipt establish publication and shared-source state separately. No installed application or service is changed by these local tests.
