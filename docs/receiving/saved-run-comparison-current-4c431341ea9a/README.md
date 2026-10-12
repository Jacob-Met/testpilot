# Current-source saved-run comparison receiving

This integration receives the existing product comparison from
[PR #33](https://github.com/Jacob-Met/testpilot/pull/33), donor commit
`a978524a75bb53d9beaa2e271b187069deafb800`, onto main commit
`c32b5459657ec26aac9837b823b1bc326510873e`.

The donor's comparison modules, focused tests, guide, and original evidence are
retained. The README and CLI conflicts are composed additively: the current
regression command, pytest keyword/marker selection, explicit targets, timeout
admission, raw Git-diff transport, report staging, and recheck behavior remain.
Neither `loop.py` nor the separately owned captured-project-source work changes.

## Native report compatibility fix

The current producer uses `null` changed-line percentages when a phase has no
executable changed-line denominator. The donor rejected these otherwise valid
reports and, if admitted, would have rendered `None%`. The integration admits
explicit nulls for only those two coverage fields and renders **Unavailable**.
Required keys and native numeric/type/range checks remain; measured zero remains
a measured zero.

`tests/test_compare_native_coverage.py` runs real current TestPilot generation,
the deterministic ScriptedModel, pytest, and coverage before passing the saved
result through the comparison CLI. It covers pure deletion, an explicitly chosen
unchanged function, measured zero/coverage, absent coverage, exact BOM/CRLF JSON
downloads, input preservation, model/test dispatch exclusion during comparison,
and malformed or absent coverage fields.

## Completed verification

Environment: Python 3.12.14, pytest 9.1.1, coverage 7.16.2 in an isolated venv.

| Source | Actual result |
|---|---|
| Donor comparison plus current producer and new native coverage cases | 2 failed, 3 passed in 4.62s |
| Corrected integration plus maintained comparison/current CLI controls | 90 passed, 13 subtests passed in 16.67s |

The two original failures are the native pure-deletion and explicit-unchanged
reports; both returned configuration exit 2 for a legitimate null percentage.
The measured and missing-coverage controls passed. `original-native-coverage.log`
retains that output. `candidate-gate.log` retains the final output chunk and
completion summary of the corrected gate.

The corrected gate command was:

```sh
python -m pytest -q -p no:cacheprovider \
  tests/test_compare.py tests/test_compare_cli.py tests/test_compare_native_coverage.py \
  tests/test_cli_timeout.py tests/test_cli_git_diff_config.py tests/test_cli_targets.py \
  tests/test_explicit_target_cli.py tests/test_pytest_selection.py \
  tests/test_regression.py::RegressionTests::test_real_cli_uses_committed_bytes_and_preserves_dirty_worktree \
  tests/test_recheck.py::test_cli_skips_generation_and_recheck_output_is_reusable \
  tests/test_recheck.py::test_output_admission_precedes_execution
```

An earlier default-runtime invocation stopped before collection because pytest
was absent. The first draft of the new fixture stopped on an incorrect test-side
attribute access before reaching comparison. Neither is used as product failure
evidence. The preserved two-failure result followed the fixture correction.

## Reusable native example

Run the receiving driver with an interpreter containing pytest and coverage:

```sh
python docs/receiving/saved-run-comparison-current-4c431341ea9a/receive_native.py \
  --out /path/to/new-receiving-directory
```

It creates two tiny controlled projects, generates current native reports using
the scripted backend, and invokes `testpilot compare` in a separate process with
an invalid default provider setting. The resulting `comparison.html` preserves
the exact native JSON downloads. The accompanying receipt records the source
commit, source hashes, interpreter/packages, actual process outputs, retained
input identity, and final artifact hashes. Every run needs a new directory.

The two reports exercise different diff selection contexts against the same
function. They demonstrate unavailable versus measured changed-line coverage;
they do not establish a quality or performance improvement. The original donor
browser evidence remains historical until a new browser receipt is recorded.
