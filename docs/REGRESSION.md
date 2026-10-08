# Check a retained regression test before and after a fix

`regression` runs the exact tests saved in one TestPilot generation or recheck
report on two committed versions of your Python project. It answers whether a
retained test actually failed on the chosen before revision and passed on the
chosen after revision. It makes zero model calls and does not repair tests or
apply the proposed patch.

Use your project's existing interpreter with pytest and its dependencies
installed. Both Git revisions must already be available locally. The command
does not fetch objects or install dependencies.

```bash
python -m testpilot regression \
  --repo /path/to/project \
  --report /path/to/saved-run/report.json \
  --before BUGGY_COMMIT \
  --after FIXED_COMMIT \
  --python /path/to/project/.venv/bin/python \
  --timeout 60 \
  --out /path/to/new-regression-check
```

`--repo` is the root of a local Git worktree. The output directory must be new,
outside that repository, and have an existing parent directory. Each pytest
phase receives the specified positive, finite timeout. The default interpreter
is the one running TestPilot; a selected virtual environment is preserved.

The two refs are resolved once, before execution, to full commit and tree IDs.
They need not be ancestors. Dirty files, staged changes, untracked files and the
current branch do not supply the source being tested. They are left untouched.
Each revision is materialized in a temporary directory directly from its Git
blobs, retaining regular-file bytes and executable modes. Git replacement refs,
archive attributes, smudge filters and caller Git-directory environment settings
cannot silently substitute the selected source.

The exact saved test bytes are admitted once by the existing retained-test
reader. Both revision snapshots and test placements are validated before either
pytest run starts. If a retained path exists in a commit, its bytes must exactly
match the saved test; different bytes or a file/directory conflict refuse the
operation. Absent retained paths are inserted only into the disposable runner
copy. The generation report's previous status is recorded as context, never
used as evidence that a current execution passed.

## Understand the result

The new directory contains `regression.md` and `regression.json`. The JSON schema
identifier is `testpilot.regression/1`; it is a paired execution result, separate
from generation and recheck results.

| Status | Meaning | Exit |
| --- | --- | --- |
| `verified_regression` | At least one exact generated case failed before and passed after, and the after run is successful. | 0 |
| `not_regression` | The comparable generated cases already passed before; an unrelated existing-test failure does not establish a witness. | 1 |
| `after_failed` | The comparable after execution still fails, including a remaining existing-suite failure. | 1 |
| `inconclusive` | Execution or generated-case comparability is incomplete. | 1 |
| Admission/setup/output refusal | A result could not be produced; existing output paths are preserved. | 2 |

Comparison uses each actual native `(generated_file, nodeid)` identity. Every
retained file must collect at least one generated case; identities must be
unique and exactly match across phases. Both native runs must finish, provide
JUnit, return 0 or 1, and contain no native errors. All generated after cases
must pass. A timeout, collection/import/setup error, missing JUnit, missing file
collection, changed or duplicate identity, or generated skip is inconclusive.
Existing-suite skips retain the current native runner's semantics.

`comparison.witnesses` contains the matched failed-before/passed-after cases.
`case_pairs`, `unmatched_before` and `unmatched_after` make identity differences
explicit. Both `before.result` and `after.result` retain the native sandbox
result, case outcomes, generated counts, timeout and JUnit availability. No
result is inferred from an older report or from exit status alone.

The result also records full requested refs, commit/tree IDs, selected Python,
source file/byte totals, input-report SHA-256, exact retained test contents and
their hashes, zero model calls and execution timestamps. `snapshot_sha256`
binds the admitted original tree inventory: a UTF-8 JSON array sorted by UTF-8
path bytes; each record has keys in order `path`, `mode`, `blob`, `bytes`;
`ensure_ascii=True`, separators `(',', ':')`, and no trailing newline. `mode`
and `blob` are Git strings and `bytes` is an integer. File content is checked
against each original Git blob identity when materialized.

## Boundaries

This version admits at most 10,000 regular files, 8 MiB per file and 64 MiB per
revision. Git symlinks, submodules/gitlinks, unavailable objects and unsupported
paths are refused rather than omitted. Paths must be UTF-8 relative Git paths;
backslashes, colons, traversal components and `.git` components are unsupported.
Git must support its `--no-lazy-fetch` option. A dependency that is only present
in your working checkout will not appear in a committed snapshot.

The established TestPilot sandbox, collection rules, ignored directories and
generated-case collector remain in force. Coverage is disabled for both phases
so optional instrumentation does not change the paired test invocation. No
operating-system or network isolation is added: project tests retain the
existing local execution boundary and can access ordinary process resources.

A passing pair is evidence about these two revisions and this exact suite. It
does not establish why a test failed, which intervening change fixed it, the
completeness of the tests, or whether another environment will behave the same.

## Python API

```python
from testpilot.regression import RegressionError, check_regression

result = check_regression(
    "/path/to/project",
    "/path/to/saved-run/report.json",
    before="BUGGY_COMMIT",
    after="FIXED_COMMIT",
    timeout_s=60.0,
    python="/path/to/project/.venv/bin/python",
)
print(result["status"], result["comparison"]["witnesses"])
```

The API returns the same dictionary without publishing files. Invalid input,
Git admission, snapshot preparation and execution setup raise `RegressionError`
(a `ValueError` subclass). Native test failures and inconclusive executions
return their honest comparison status instead of raising.
