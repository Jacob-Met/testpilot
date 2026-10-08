# Independent native Git compatibility receiving

Author: estate-6cc6795e89f4/coordination_evidence. Expectations fixed before reading or importing the repair candidate. The original eacb9907 parser and README were inspected. Candidate commit supplied by owner: 9265ae42bde5b6bd559584a11cbb7c30b7849743.

The oracle is actual native Git output and git apply --check against its matching old fixture tree; GNU diff -u is also exercised. A Git validity check and TestPilot semantic target expectations are separate: this review does not ask TestPilot to implement git apply or verify source content. The parser must continue to accept complete valid hunks under supported git-diff/diff-u input and preserve target mapping.

Fixed cases: multi-file and disjoint multi-hunk Python changes; zero, one, default and function context; additions, deletions and pure deletion anchors; files without a final newline; CRLF bodies; literal +++/--- body text; a UTF-8 filename with a tab; Unicode line separators inside a Python string; a binary patch mixed with Python changes; mode-only, rename-only and copy-only metadata; GNU diff -u with timestamp headers. Git mail-format envelope is an additional compatibility observation with original-parser control, separately distinguished from the documented git diff/diff-u contract.

Expected target names come from deliberately authored fixture functions. Metadata-only changes and binary content must not invent Python changed functions. Every valid case must pass native Git apply --check (with --unidiff-zero for U0) before being counted as a valid compatibility case. All generated diff bytes, Git version, commands and raw stdout/stderr are retained.

A malformed hunk with an impossible declared body balance must be rejected before CLI run effects. Expect exit2, a concise format-error diagnostic, no traceback and no new output directory/report. Existing output sentinel bytes must remain identical. A missing model-script path and a fixture pytest collection tripwire distinguish early diff refusal from later model or subprocess work. The negative is verified with native Git as well. Both automatic selection and an explicit current target are checked, because a context diff stays part of the request under explicit selection.

No live services, external model, credentials, network, project source or other worker's tests will be modified. Review scripts and fixture repositories are local receiving artifacts. Do not repeat the owner's full 398-test suite.
