# Final independent TestPilot receiving — v3

Frozen product source: d40d8fd054262b9aae4544d98d691568fd4e1dd3.
Exact source-equivalent integration head received: d801fe3b409ce40507df75b5d268063dab463c48, incorporating the source owner's accepted main 191cca4.
Independent worktree: /home/jacob/testpilot-git-compat-v3-6cc6795e89f4.

Result: all 11 original positive patch cases pass, all 4 malformed CLI cases pass, malformed API refusal passes, and source hash guards pass. Native receiver exit 0 in 9.53 seconds.

## What was received

The original expectations, native Git/GNU diff bytes, fixture repositories, Git apply oracle and baseline parser were retained. This run changes only the candidate source identity and writes separate v3 outputs. It does not replace either v1 or v2 evidence.

The 10 documented git diff / GNU diff -u cases cover multiple files and separated hunks; zero, one, default and function context; additions, deletions and pure-deletion anchors; no final newline; CRLF; literal +++/--- body text; a UTF-8/tab filename; Unicode separators inside a Python string; binary content beside Python; mode-only, rename-only and copy-only metadata; and GNU timestamp headers. The original parser and v3 agree on every file record, line set, function, source span and independently authored target-name expectation.

The additional native git format-patch case with the plain custom signature 'HAMON Receiving Fixture' now passes with the same exact bytes that failed in v1 and v2. The receiver's coverage is this complete frozen fixture set; the source owner's additional footer ambiguity and integer-boundary tests remain separately attributable.

The malformed unfinished-tail patch is still refused by the API and by native Git. Automatic and explicit CLI modes both return a clean format diagnostic with exit 2, before attempting to load the deliberately missing model script. Existing report/patch sentinel bytes remain identical, new output directories remain absent and the pytest collection tripwire is absent.

## Original observations across revisions

| Receiving revision | Documented positive cases | Original custom-mail case | Automatic malformed CLI | Explicit malformed CLI |
| --- | --- | --- | --- | --- |
| v1 | 10/10 | Refused | 0/2 clean format refusals | 2/2 |
| v2 | 10/10 | Refused | 2/2 | 2/2 |
| v3 | 10/10 | Passed | 2/2 | 2/2 |

## Source and evidence

diff.py SHA256: 586f5b981d2c8d66e47cd8c5566ace994b152cde87f43db9b6e1c02ac5337490
__main__.py SHA256: 32bb84da429e297e82aa9121e54764e615eadfd9ea8400b7f0ce804560d7cf16

Both hashes were checked before candidate import and after receiving, with no intervening source change. independent-receiving-v3.json contains full raw API/CLI observations and comparisons. pre-import-contract-v3.json binds the original expectations, builder, receiver and fixture provenance. receive_candidate_v3.py.txt is inert source for reproducing this receiving step.

No product source was edited by this reviewer, no source publication was attempted and the owner's full suite was not repeated here. The source owner can receive this evidence commit into the final integration branch alongside its own targeted and full-suite evidence.
