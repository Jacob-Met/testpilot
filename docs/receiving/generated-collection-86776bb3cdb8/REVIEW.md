# Generated tests must be exercised before a patch can pass

Claim: https://github.com/Jacob-Met/testpilot/issues/13

Qualified production source: `c556e9b883fb372b938c50240977ddb5785c43bb`, tree
`b394b312f490338557cc6be7b03e53f6b51e1b4a`. This combines the collection correction
with adopted main `f1a8c8e6e7533eac5a23864ef56f4e769d0d9125` and preserves the
original CI workflow and evaluation timeout exactly. The later packaging commit
adds evidence only.

## Reproduced product failure

On original main `9f01fcb6de085850eca00db746380795eb548d62`, a synthetic project
configured with `testpaths = ["checks"]` made the actual TestPilot CLI report
`passed`, exit zero, and write a patch with zero reported generated tests. Applying
that exact patch and explicitly running its generated module failed on its
deliberately wrong assertion. The configured existing test alone had supplied the
green result. `baseline/` retains the original CLI/report/patch, direct failure,
scripted replies and complete small input project.

## Resulting behavior

The generated run keeps pytest's configured collection roots and appends its
requested generated files through a small native plugin. The selected project
interpreter still supplies pytest; it does not need TestPilot installed. Project
fixtures, selection hooks, assertion rewriting and explicit selectors remain
active. Ordinary directory/file overlap executes generated cases once.

Each reported generated case carries its source-file provenance in JUnit. Counts
therefore survive custom JUnit prefixes and parameter changes in existing tests.
Success requires the complete selected suite to pass and at least one generated
case to pass. Helper-only, entirely skipped or entirely deselected output goes
through the existing repair loop, then returns `no_tests` if it remains unqualified.

The historical `tests_written` metric retains its static definition fallback when
a timeout or abrupt exit prevents a complete JUnit report. The explicit
`junit_available = false` distinguishes that situation from a valid empty report,
which correctly reports zero generated cases. Neither situation qualifies success.

## Verification and correction history

| Source | Native result | Meaning |
|---|---|---|
| Original `9f01fcb6` | CLI exit 0; emitted module fails | Reproduces the unexecuted-patch false green |
| Initial `2e32efee` | Full suite: 147 passed, 1 failed | Exposed a reporting regression: the intentionally timed-out evaluation lost its four authored-test count |
| Corrected `76df7c0` | Affected gate: 17 passed | Includes absent-report timeout/exit, valid empty report and the unchanged scripted evaluation |
| Current-main `c556e9b8` | Full suite: **162 passed** in 62.33 s | Actual CLI, patch consumer, prepared project interpreter, coverage, original evaluation and existing source/path/provider controls all pass |

The final complete native log has SHA256
`20fd86f6317567ab0a844671db5809e5f407977dd2d677b6360dc7924a52e851`.
Each raw log has a receipt recording its exact source, command, working directory
and source environment. The initial failed gate is retained; it is not a final
qualification result. The initial auxiliary lint receipt applies only to its named
source and does not assert a clean final lint gate.

The independent receiver supplies separate baseline/candidate controls and source
review under `independent/`. Its maintained test is
`tests/test_generated_collection_receiving.py`; the final native suite includes
that exact portable file.

## Preservation and evidence use

Only six product/documentation/test paths differ from current main. All 292 other
current-main leaves are unchanged. `source-preservation.json` records the complete
298-leaf qualified source manifest and exact unchanged definitions, including
process cleanup, environment handling, path protection, partial repairs, model
calls and original CI/evaluation inputs. PR #10's provider contribution remains
with its owner.

All runtime inputs are synthetic and all model replies are scripted. The gate
verifies the local generation/execution/repair workflow; it does not measure a live
provider or model. Archived `.py.txt` files are inert copies, mapped in
`artifact-paths.json`. The maintained controls are collected only from `tests/`.
