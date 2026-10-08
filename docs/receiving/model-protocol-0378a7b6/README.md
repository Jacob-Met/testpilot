# Model response receiving

This native contribution addresses TestPilot issue #54. Its only runtime change is
the model-response boundary in testpilot/model.py; it preserves the existing loop,
sandbox, retry budget, report writers, request format and admitted-usage policy.

## Evidence

independent-admission.zip contains the original real-CLI data-loss reproduction
on baseline 513f174 and 23 independent CLI cases on candidate v1 (model SHA-256
0903eaf6...). Its original input contract and the separately documented compatibility
overlay are both retained. Existing integer coercion was deliberately preserved.

independent-decoding.zip contains six independent CLI cases on the final model
SHA-256 4cd8367f..., including native JSON decoder limits, truncated HTTP 200/400/503
bodies and successful repair. Four retained outputs, exact previous work, ledger
and retry behavior were checked. The receiver's initial too-shallow nesting
calibration failed before CLI execution and is preserved beside its corrected run.

author-receiving.zip preserves the authored changes, exact source versions,
drivers, raw logs, original four-file outputs and corrections. Candidate v1 first
recorded 53 passes and 7 author-test failures because the assertion used files
instead of the existing test_files field. Corrected assertions produced 61 passes.
The final model run produced 66 passes and 1 test-fixture failure: depth 1010 did
not reach the native JSON recursion limit. Only the fixture depth changed to 4000,
and that corrected case passed separately. These are historical runs, not one
full final-source pass; current-parent qualification is recorded separately.

Every independently supplied manifest and listed file was hash-checked before
adoption. Archive members were read back byte for byte. adoption.json records
archive and source hashes. Acceptance prose is copied unchanged alongside them.

## Publication boundary

The no-GitHub-Actions instruction was recovered from HAMON issue 143 comment
6067592767 during this work. No TestPilot source branch, PR, merge, or Actions
trigger has been published by this lane. Native work continues. Hosted gates are
unrun and remain required; a quota reset does not release the Actions hold.
Current-parent composition and receiving are recorded as subsequent native work.
