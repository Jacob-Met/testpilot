# Git-quoted source paths reach test generation

An actual edit to `café.py` currently produces Git's quoted header
`"b/caf\303\251.py"`. The original path parser retains the quotes and escapes,
so it selects no Python function. The complete TestPilot pipeline consequently
returns `no_changes` without writing any tests for the edited function.

The change decodes the quoted filename bytes before the existing `a/` or `b/`
prefix removal and `/dev/null` handling. It handles Git's C control escapes and
three-digit octal bytes, including quoted UTF-8 and filesystem byte names.
Malformed quoted headers now raise an explicit `ValueError`; they are not
silently interpreted as another filename. Unquoted header/timestamp handling,
hunk accounting, source selection and default test-file exclusion retain their
existing behavior.

Git documents this byte quoting under
[core.quotePath](https://git-scm.com/docs/git-config#Documentation/git-config.txt-corequotePath)
and [diff format](https://git-scm.com/docs/diff-format). Real Git produced the
test inputs with both values of `core.quotePath`; the implementation does not
change the user's Git configuration.

## Qualification

Base: `a565cc365fdf9cf346b6104a6abdd77d0b12d2fd`, tree
`6e00a31af1785dae2aed3beeac76a477fbb17f00`. All 78 original repository blobs were
fetched and individually verified before materialization. Only `testpilot/diff.py`
changes at runtime; the new regression file and this receiving directory are
additions. The existing loop/sandbox/CLI/model, README and CI work are unchanged.

| Selection | Original | Candidate |
| --- | --- | --- |
| 31 added pathname cases | 4 pass, 27 fail | 31 pass |
| Added cases plus 6 existing diff cases | — | 37 pass |
| Complete native repository pytest suite | — | 67 pass |
| Independent real-Git all-byte filename matrix | — | 254 paths parsed and selected |

All these native Linux runs had zero skips. Python 3.12.14, pytest 9.1.1 and
coverage 7.16.2 were used in an isolated virtual environment. The tests include
ordinary Unicode Python modules, raw Unicode alongside escapes, tabs/newlines/
quotes/backslashes, a changed rename, added/deleted paths, test-file exclusion,
unquoted spaces and diff-u timestamps, malformed quotes, and POSIX filename
bytes that are not valid UTF-8. The control/quote/backslash and raw-byte cases
are explicitly scoped to POSIX filenames; Windows execution is not claimed.
`receipt.json` binds exact source, test and log hashes to these results.

Run from a checkout with the documented test dependencies:

```sh
python -m pytest tests/test_git_quoted_paths.py tests/test_diff.py -q
python -m pytest -q
```

The lead independently reviewed the decoder and authored a separate Git
staged-diff matrix covering every POSIX filename byte from 1 through 255 except
slash. All 254 actual filename identities were recovered by the public parser
and by the AST target-selection boundary, with the exact function and added
lines `[1, 2]`. No case skipped. The unchanged witness and its fresh output are
`independent_git_byte_paths.py` and `independent-byte-paths.json`.

```sh
python docs/receipts/git-quoted-paths-bd1abdb2f886-20261008/independent_git_byte_paths.py \
  testpilot/diff.py
```

## Representative workflow

`check_workflow.py` creates a disposable real Git repository, edits `café.price`,
feeds its actual Git diff to the unchanged TestPilot pipeline, and supplies two
authored ScriptedModel replies. TestPilot runs actual pytest and coverage child
processes through its unchanged sandbox. The original returns `no_changes`,
zero tests and zero model calls. The candidate returns `passed`, one passing
generated test and two scripted calls. Its resulting patch passes actual
`git apply --check`; the original source directory retains the edited module
and receives no generated test writes.

```sh
python docs/receipts/git-quoted-paths-bd1abdb2f886-20261008/check_workflow.py \
  . /tmp/testpilot-quoted-workflow.json
```

Both workflow receipts and the original real-Git failure are retained here.
These results qualify this Python/Linux source path. They do not establish a
live provider result, model quality, deployment or native task ownership.
Existing module-name semantics, combined-diff support, malformed-hunk handling
and unquoted-header semantics are outside this correction.

Source ownership was recorded in
[TestPilot #2](https://github.com/Jacob-Met/testpilot/issues/2#issuecomment-6054899236)
under `chatgpt-astra-bd1abdb2f886-20261008 / estate_source`. The generated-test
preservation owner retains `loop.py` and their README span. The lead accepted
this source after independent review; source integration is recorded in the PR.
