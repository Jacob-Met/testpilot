# Independent receiving: generated pytest collection

Accepted product source: `c556e9b883fb372b938c50240977ddb5785c43bb`, tree `b394b312f490338557cc6be7b03e53f6b51e1b4a`. This is source acceptance for publication on the observed current main, with remote publication/tree/hosted-gate receiving still to follow.

## Demonstrated behavior

The original `9f01fcb6de085850eca00db746380795eb548d62` source can report a generated patch as passing while pytest's configured `testpaths = ["checks"]` never collects that patch. The independent actual CLI control retained the original false green: zero repairs, zero written cases counted, and one existing pass, with the incorrect `double(2) == 5` assertion still in the patch. The candidate runs that assertion, records its failure, invokes the scripted repair once, and finishes with the corrected `double(2) == 4` patch, one generated case, and two total passes. The original project remains unchanged. Both actual reports and patches are retained under `cli-evidence/`.

The independent controls were authored before inspecting the candidate implementation. The same frozen 11-case file produced **9 failures and 2 passes** on the original source, then **11 passes** on first candidate `2e32efee7fec4b97f3756083c66f4b860359957b`. This uses real pytest subprocesses and a real scripted CLI invocation, with synthetic projects and no model service.

The controls preserve the configured failing existing suite while excluding an unrelated unselected ambient test; execute a generated file once when its directory is already selected; retain a project fixture and collection hook; accept a helper beside an executed test; refuse helper-only, module-skipped, entirely skipped or deselected generated output; retain explicit `-k` selection; and preserve the ordinary baseline run with no generated files. A separate provenance control changes an existing parameterized test from one case to two when the generated file appears. With a JUnit prefix present, the final three passing cases count as **one** generated case. This prevents existing-case drift from being mistaken for newly authored coverage.

## Corrected absent-report boundary

The author's first complete native gate exposed a real compatibility regression: an intentional timeout yielded no JUnit cases, so the initial implementation reduced the established `tests_written` total from 19 to 15. That failed gate is retained in the author's packet. Successor `76df7c0fb389f31f2101894f305ca3d49eac9185` adds `junit_available` and uses native source-provenance counts only when a report exists. A timeout or abrupt process termination preserves the static authored-definition count without claiming verified execution.

I independently ran three actual native processes on final source `c556e9b8`: a complete empty JUnit report from native deselection, an abrupt exit before JUnit, and a timeout before JUnit. All three controls passed. The complete empty report reports zero written cases; each absent-report case retains two authored definitions. All three have zero verified generated cases and `ok = false`. The runner, collection hooks, provenance parsing and success qualification are byte-identical to the first candidate tested by the 11-case suite. Reversing only the explicit availability field/wiring and count guard recreates those previously tested production files exactly.

## Source and current-main preservation

The final product adds or changes exactly six paths relative to current main `f1a8c8e6e7533eac5a23864ef56f4e769d0d9125`: README, the copied native pytest runner, sandbox, loop, author controls, and maintained independent controls. All six files retain their exact `76df7c0` bytes. All **292 other current-main leaves** retain their exact blobs and modes. The adopted original CI workflow and eval timeout adjustment are preserved unchanged. The final tree has **298 leaves**.

A fresh GitHub ref, commit and complete recursive tree read independently confirmed that the local current-main parent matches all **295 remote leaves**, with `truncated = false`. The preserved workflow runs `python -m pytest -q` on Python 3.12 for pull requests, with pytest and coverage installed. This readback does not claim that hosted checks for the forthcoming publication have run.

The unchanged-definition guards include the original sandbox process-group/deadline implementation, environment preparation, safe path join, coverage helpers, and the loop's existing generated-path and partial-repair machinery. Removing the two explicit loop additions reconstructs the entire original loop file byte-for-byte. The prior baseline and candidate runtime receipts match their immutable source blobs; their child processes loaded the owned receiving checkout, not an unrelated editable installation.

## Maintained controls and final native gate

The maintained `tests/test_generated_collection_receiving.py` is the independent control file with only the actual CLI subprocess's source binding and working directory made portable. Its SHA256 is `2af73df91390e3b44526c5ba1e4d325fb48d99fb668d6d3d565668b8347c9a83`. The original and portable normalized test ASTs match after removing those environment bindings and supporting imports. The affected actual CLI case passed once from a foreign working directory; the other ten controls were not rerun just for this harness adjustment. The maintained file is byte-identical in final source.

The author's final complete native run on exact `c556e9b8` passed **162 tests in 62.33 seconds**, including the maintained independent controls and the corrected evaluation behavior. Its log SHA256 is `20fd86f6317567ab0a844671db5809e5f407977dd2d677b6360dc7924a52e851`. I read its exact source-bound receipt and checked the raw log hash; I did not repeat that broad run. The independent outcomes remain associated with their actual tested source pins in this packet.

`run-baseline-controls.py` and `run-candidate-controls.py` preserve the exact drivers originally held in orchestration memory; the corresponding receipts' driver placeholder refers to those files. `run-report-boundary.py` is the bounded successor driver. `verify-source-preservation.py` reproduces the static guards using immutable local Git objects. Python sources may be archived with a `.py.txt` suffix in the repository packet to avoid duplicate pytest discovery; preserve their bytes and map any renamed paths explicitly.
