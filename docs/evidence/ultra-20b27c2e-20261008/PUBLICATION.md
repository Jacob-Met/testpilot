# TestPilot: preserve existing tests and partial repairs

Source contribution by `ultra-20b27c2e-20261008 / estate_production`, coordinated in TestPilot issue #2. The production change is confined to `testpilot/loop.py`, one new test file, and the README behavior note. The source remains frozen for the root publisher.

## User-visible result

Generated tests cannot replace an existing repository path. TestPilot assigns a new filename and keeps the original suggested path as a stable repair alias. Partial repairs retain all other generated test files, including failures, so a repair cannot become green by silently omitting a regression. Conflicting original-alias/canonical blocks in the same response are refused atomically; identical contents converge safely. The emitted product patch contains additions only and Git refuses a destination created after evaluation.

The existing sandbox and its generated-code trust model are unchanged. These receipts use authored model responses and actual local pytest/Git execution; they do not establish live model quality or hostile-code containment.

## Frozen files

| Repository path | SHA-256 |
|---|---|
| `README.md` | `f259cfb20d0b2b5d740285c29ab2ece6a69a92e21d72bf99db7ca6adfae7c5b6` |
| `testpilot/loop.py` | `dd79fbfbdcab00978b288835645c1b5adf37fec404ec0fa6da0ac41d45a79cbf` |
| `tests/test_generated_test_preservation.py` | `f6efd91dc4554a6cc0d1c162ae41aeec25dc94d81bad3cc5c7cd61ea674cdab7` |

The original tested base is `a565cc365fdf9cf346b6104a6abdd77d0b12d2fd`. The first GitHub checkpoint still resolved main to that commit. Open CI PR #1 is disjoint: only its workflow and `tests/test_eval.py` differ, with the latter raising the existing scripted-evaluation timeout from five to ten seconds. Its exact head `8fb4b8e2412283628375ce658d9ed95b2e1116a6` plus these three frozen candidate files passes **54 tests in 29.12 seconds** in a separate detached worktree. No remote branch or owner source was changed by that compatibility run. See `current-main-pr1-readback.json`, `current-main-pr1-composition.json`, and the raw `ci-pr1-composed-suite.log`.

The final freshness check caught another product contribution landing on main: `feea1889358b570d652f456ce5b63e853ba47d47`, tree `435b9278205d9535883ed0e49c533ed3fdeeb05e`. It changes only `testpilot/diff.py`, adds `tests/test_git_quoted_paths.py`, and retains eleven peer evidence files. All three proposed production paths remain unchanged in that receiving base. A second isolated worktree composed those current-main bytes with the frozen proposal and passes **85 tests in 28.49 seconds**, including every new Git-quoted-path case. `current-main-composition.json` records all 90 receiving blobs and the exact composition; `current-main-composed-suite.log` is the raw result. Publication builds on that full current tree and preserves all 88 unowned existing blobs.

## Verification and retained failures

| Run | Result | Source and evidence |
|---|---|---|
| Original product suite | 36 passed in 15.97 s | Original baseline; observed author tool result, no retained raw log. |
| Initial preservation regressions on untouched baseline | 13 failed, 3 passed in 7.09 s | `baseline-new-regressions.log`; exact 16-case file retained under `baseline/`, and baseline implementation under `baseline-loop.py`. |
| First candidate full suite | 52 passed in 23.54 s | `candidate-tests.log`; this predates the final alias-conflict guard. |
| Final preservation suite | 18 passed in 8.35 s | `candidate-preservation-final.log`; exact frozen implementation. |
| Root independent full suite | 54 passed in 24.75 s | `root-final-suite-transcription.json`; root's completed tool output, session 33648, exit 0. Root captured no raw log; this is explicitly a transcription supplied to the author. |
| Frozen candidate composed with CI PR #1 | 54 passed in 29.12 s | Raw `ci-pr1-composed-suite.log`; exact frozen implementation and PR #1's disjoint changes. |
| Frozen candidate composed with current main | 85 passed in 28.49 s | `current-main-composed-suite.log`; includes newly merged Git-quoted-path support/tests at `feea1889`. |
| Independent runtime-integration review | 7 passed, no failures/errors/skips | `independent-runtime-integration/{REVIEW.json,independent-results.xml,test_independent_preservation.py,PUBLICATION.md}`; actual generated pytest subprocesses and Git apply. |

The full suite and review environment is Linux, Python 3.12.14, pytest 9.1.1; coverage 7.16.2 is installed, so coverage tests run. The independent review additionally records Git 2.51.1. These runs are separately attributed and are not summed into a larger case count.

`baseline-reproduction.json` retains two actual false-green results: replacing an original failing test, and dropping the second failing generated file during a partial repair. `ambiguous-alias-pre-fix.json` retains the later independent ambiguity finding: reversing two conflicting alias/canonical repair blocks changed the outcome. The exact pre-guard source has SHA-256 `14b393435cd181efeca023306415d390438c675aac78c1e1e62320dc781f3b2e`; it was reconstructed by removing the four guard lines from the frozen candidate and hash-verified before saving as `pre-ambiguity-loop.py`.

## Public CLI and generated-patch receiver

`cli-fixture/` contains the original tiny repository, actual diff, and four scripted responses. The public CLI emits the reports and patch retained in `cli-output/`. It performs two partial repairs and retains both generated files. The exact generated patch passes `git apply --check`, applies successfully in `cli-applied/`, and the resulting suite passes all three tests. The original CRLF test bytes remain identical, SHA-256 `91a33989098b3a71428c2eecf1242ed97b290445b02c925e0d4e8f742ca7bfaa`.

This CLI run used the pre-ambiguity-guard implementation `14b393…`; it is not relabeled as a run of the final file. The final guard is covered by the frozen-source author regressions and the independent runtime review, including successful Git application and late-collision refusal. `cli-receipt.json`, `cli-run.log`, and `cli-applied-tests.log` retain the exact invocation, statuses, output hashes, and limitations.

## Publication scope

The handoff manifest maps every source/evidence file to its proposed repository destination with byte length and SHA-256. TestPilot production paths and evidence are destined only for `Jacob-Met/testpilot`. The accompanying recall and memory reviews are mapped separately to their existing private repositories. No implementation, code review, publication, or runtime adoption beyond the named source hashes is implied by this handoff.
