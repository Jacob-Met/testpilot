# Current-parent native qualification

The final model source and tests were composed with current main 906ce149, which
includes the existing cancellation, pytest selection and paired regression work.
All 1,497 unowned current-parent leaves and the exact owned README insertion were
preserved. The source tree before receiving is 937c241ef63ebfc78f8a0deecbbf39144c0eecb2.

On native Windows CPython 3.12.10, the complete model-focused command passed all
67 tests. The full repository command completed with 478 passed, 36 failed,
35 skipped and 17 passing subtests; all 1,509 tracked files remained unchanged.
Every one of those 36 FAILED/SUBFAILED summaries was reproduced on an untouched
checkout of the same current parent, with the original model file. That bounded
baseline run selected the 30 containing test nodes and reported 36 failed,
2 passed and 5 passing subtests. These are retained native baseline failures,
not a claim that the complete repository suite passed. The full baseline suite
was not repeated. Raw commands, versions, failures, skips, outputs and source maps
are in current-parent.zip.

The production model SHA-256 remains 4cd8367f511d32ada95b5d37bdd7faf06f38aa8f15c046cee3dd3eefe2f3cb6c.
The final test file remains 1e875743a2b6a6217fd9c6ca6557cc79dc1e414837ec19796c8273eb93a916d1.
The earlier independent CLI receiving remains bound to its original source pins.

Receiving corrections are retained without editing existing product or tests:
the first merge command lacked an explicit committer identity; the subsequent
preservation helper applied whitespace checking to incoming historical patch
receipts, whose blank context lines must remain exact; its correctly scoped check
of this contribution passed. The first baseline selector incorrectly equated 36
reported failures with 36 test nodes, missing subtests. After including all their
parents, a too-long Windows checkout path failed before testing. A new shorter
owned path admitted the exact original tree and reproduced all 36 failures.
These setup failures and their scripts are included alongside the final receipts.

The sole current workflow, .github/workflows/ci.yml, is unchanged and triggers
only for push to main and pull_request. Under the recovered no-Actions instruction,
a unique non-main source branch and issue checkpoint may be published. No PR,
main merge, workflow changes or Actions run is authorized by this qualification.
The required hosted Python 3.12 gate remains unrun. Quota recovery does not lift
the Actions instruction.
