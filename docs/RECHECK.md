# Recheck saved tests after a code fix

`testpilot recheck` runs the exact tests retained in a previous `report.json`
against the project checkout you select. It does not generate or repair tests
and makes no model calls. This lets you verify a code fix without paying for
another generation run or losing the original bug report.

## Run it

Keep the original report, fix the application code, then choose a new result
directory outside the project being checked:

```sh
python -m testpilot recheck \
  --repo /work/project \
  --report /work/reports/original/report.json \
  --out /work/reports/fix-check
```

To use the project's Python environment:

```sh
python -m testpilot recheck \
  --repo /work/project \
  --report /work/reports/original/report.json \
  --python /work/project/.venv/bin/python \
  --timeout 30 \
  --out /work/reports/fix-check-with-venv
```

`--python` accepts an executable path or a command found on `PATH`, using the
same resolver as `testpilot run`. The final executable symlink is preserved,
so selecting a virtual environment keeps that environment's identity. Omit it
to use the Python running TestPilot. The selected environment must already
have pytest and the project's dependencies; this command installs nothing.

`--timeout` is a positive finite number of seconds for the pytest child,
defaulting to 60. It does not include report admission or copying the project.
The existing sandbox's process-group timeout and cleanup behavior still apply.

## What is checked

The saved report's `test_files` mapping is the execution input. Original status,
diagnosis, coverage and model history remain historical information, even if
the old report says `passed`. Recheck always evaluates the selected current
checkout through the existing pytest sandbox and generated-case collector.

Missing retained files are added only to the throwaway project copy. Their
UTF-8 bytes, including mixed line endings and a missing final newline, are
preserved. If a retained file is already applied to the checkout, its bytes
must match exactly. A matching regular file is reused in the copy without
rewriting it, including when that file is read-only.

A different current test at a retained path, a symlink in that path, or a
non-directory parent causes refusal before pytest. Recheck does not rename
tests or replace a current test with the old version. Keep a stable checkout
during the run: admission and a post-run retained-path check are not an atomic
snapshot of concurrent edits. Other repository files are copied according to
the existing sandbox's normal rules and ignored-directory list.

Project test roots, fixtures, parametrization, selection hooks and JUnit case
attribution remain controlled by the existing runner. This command does not
replace pytest collection. The complete selected suite must pass, and at least
one retained generated case must pass. Passing only existing tests, helper-only
saved files, or entirely skipped retained cases cannot establish success.

Recheck uses the existing process-level sandbox, including its environment
filtering. It executes project and retained Python code with the caller's
ordinary privileges; it does not add a security isolation boundary.

## Results and exit status

The required `--out` path must be a new directory outside the checked project.
An existing directory or symlink is refused, so neither a prior result nor
the source generation report is overwritten. Recheck writes:

- `recheck.json`: schema `testpilot.recheck/1`, current status, native case and
  generated-case results, timeout information, selected Python, UTC start/end
  times, the source report SHA-256, retained file hashes/placements, exact
  `test_files`, and `model_calls: 0`.
- `recheck.md`: a concise current-result summary with source and retained-file
  identity. It does not repeat the old model's diagnosis as a new conclusion.

| Exit | Meaning |
| --- | --- |
| `0` | The selected suite and retained-case success requirements passed. |
| `1` | Tests failed, errored or timed out, or no retained case passed. The current result is written. |
| `2` | Input, path, interpreter selection, execution setup or output delivery failed. Read stderr where available. |

The `no_tests` status means that no retained case passed without a recorded
test failure; a passing existing suite is insufficient. It is a non-success
result and uses exit 1. A malformed test or collection error uses `failed`.

Result creation is exclusive but is not a directory transaction: an output
error can leave a new partial result directory. A console write/flush failure
uses exit 2 even when result files were already written. Inspect those files
and select a fresh output path for another command. No power-loss durability
or concurrent pathname-substitution guarantee is made.

A `recheck.json` can be supplied to a later recheck because it retains the
same exact test contents. Each new result identifies its immediate source
report by hash. The original `testpilot.patch` remains the application
artifact; recheck produces no replacement patch and does not apply one.

## Saved-report admission

Recheck accepts the existing generation-report shape or its own version 1
schema. Input must be a regular UTF-8 JSON file, no larger than 16 MiB, with
1–128 retained test files and at most 4 MiB of total UTF-8 test contents.
Duplicate JSON keys, non-finite JSON numbers, invalid Unicode, unknown recheck
schemas and paths outside the generated-test naming contract are refused.
Paths must match `tests/(subdirectories/)test_name.py`, using ASCII letters,
digits and underscores for names. Contents must be strings.

These limits bound saved-report admission, not the size of the project copy
or the output of arbitrary project code. As with a normal TestPilot run,
review the retained tests and select the intended project before executing.
