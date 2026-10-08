# TestPilot physical-line selection: native receiving

## User-visible repair

A valid Python string can contain form feed, NEXT LINE (U+0085), LINE SEPARATOR
(U+2028), or PARAGRAPH SEPARATOR (U+2029) without starting a Python physical
line. TestPilot previously used `str.splitlines()` for both Git patch records
and Python source spans. In an actual Git diff, a separator inside unchanged
context consumed extra hunk line counts and hid a changed function. In a
selected function's literal, it truncated the source sent to the planner/editor.

The repair changes two expressions in `testpilot/diff.py`:

- Parse Git records at LF delimiters.
- Normalize Python CRLF/CR physical newlines to LF, then split only at LF.

The source diff is four insertions and two deletions, including two explanatory
comments. The test addition is independent of the existing diff/path suites.

The source-decoding owner's read expression/imports/docstrings in
`changed_functions` and the CLI target-preview owner's module are untouched.
Model configuration, generation, sandbox execution, coverage/reporting, existing
tests, browser replay and CI are also unchanged.

## Frozen source and authority

| Item | Pin |
| --- | --- |
| Claim | https://github.com/Jacob-Met/testpilot/issues/16 |
| Native baseline | `47a197fd46b107a797b1547db02cb5ed5ad2abe1` |
| Native source commit | `caab0c4d2f76f0a410edd9ac5f793b716a938212` |
| Source tree | `7d2a19c2684f00e1551303eeef1cd75b075d8e9c` |
| Original diff.py Git blob | `425d0712b18a6a72226399a2f9d704193ace1133` |
| Corrected diff.py Git blob | `3fade84c1ecd40e3b20e2c41b2225fd1fed0e669` |
| New regression Git blob | `d25916fd9bc0cf98647e2678ce942fa6f2d2ba1c` |

The implementation was made and committed in the isolated native worktree
`/srv/hamon-estate/testpilot-physical-lines-a3425ebf9874`, on branch
`work/physical-lines-a3425ebf9874`. The native receiver is
`/srv/hamon-estate/receivers/estate-a3425ebf9874-testpilot-physical-lines`.
This is an external source contribution, with no resident task lease or native
goal adoption claim. Its exclusive coordination record is
`/srv/hamon-estate/coord/estate-a3425ebf9874-testpilot-physical-lines.json`.

## Qualified behavior

| Receiving boundary | Original source | Corrected source |
| --- | --- | --- |
| Identical 12 new cases, native Python 3.14.4 | 9 failed, 3 passed | 12 passed |
| New cases plus 66 existing diff/path/matching controls | Not rerun as a full baseline suite | 78 passed |
| Real CLI against the same authored Git change | `no_changes`, exit 1; no model calls or patch | `passed`, exit 0; one selected function, two scripted calls, two generated tests |
| Delivered patch | Empty because selection failed | `git apply --check` and actual apply succeeded; 3 existing/generated tests passed |

The baseline tests were written before changing production source. Four
parameterized real-Git controls cover literal separators in unchanged context;
four independently compile and compare selected source containing the same
literal characters. Three controls preserve Python LF/CRLF/CR spans, and one
actual CRLF Git fixture contains Unicode context. The focused command also ran
the unchanged diff, quoted-path, source-boundary and match-target test modules.
It is a focused 78-case qualification, not a full-project suite claim.

The actual command was `python -B -m testpilot run --git-base HEAD --backend
scripted --rounds 0` with explicit authored project, response directory and
output paths. The original and corrected modules were selected through separate
explicit `PYTHONPATH` values. Before invoking TestPilot, the source was compiled
and returned the changed value 2. The corrected report selected `answer` at
physical lines 3–4, with changed line 4. The receiving script checked exact
source and existing-test hashes before and after both command runs and patch
application.

These checks establish source selection and delivered-patch behavior. No provider
was contacted, no model capability was evaluated, and no personal repository,
live application state or installed TestPilot runtime was changed.

## Reproduce the command boundary

Use separate checkouts of the pinned original and corrected source. Choose a
new, absent work directory; the script refuses to reuse one.

```sh
python -B docs/receipts/physical-lines-a3425ebf9874-20261008/cli/receive_physical_line_cli.py \
  --baseline-source /path/to/testpilot-original \
  --candidate-source /path/to/testpilot-corrected \
  --work /path/to/new-disposable-receiving
```

The standalone receiver uses only the standard library, native Git and the
project's pytest dependency. It creates its own Git project and scripted
responses, preserves both command reports/patches and outputs, applies the
delivered patch to a separate authored receiving copy, and exits nonzero if any
contract differs. Its receipt includes exact commands, source hashes and the
actual report/patch hashes. The historical baseline diagnostic under
`baseline/` is retained unchanged; it captures the original native paths and
is not the portable replay entry point.

For the focused candidate cases, from the corrected source root:

```sh
python -B -m pytest -q -p no:cacheprovider \
  tests/test_physical_lines.py tests/test_diff.py \
  tests/test_git_quoted_paths.py tests/test_diff_source_boundary.py \
  tests/test_match_targets.py
```

To rerun the negative unit boundary, use the unchanged new test file with the
original `testpilot` package. Do not apply the production patch to that baseline.
The expected outcome is nine failures and three physical-newline controls
passing.

## Evidence interpretation

`baseline/diagnostic-report.json` preserves the first real-Git omission and
literal-source truncation, plus ordinary LF/CRLF controls. The diagnostic
process's exit 0 means the observations were collected; it is not a passing
product qualification. `baseline/pytest-junit.xml` records the subsequent
assertion failures on the unchanged baseline. Both remain negative evidence.

`focus/` contains the 78-case candidate result. `cli/` contains the
independently observable command outputs, JSON/Markdown product reports,
generated patch and receiving result. The original project's source/test bytes
are identified in the command receipt. Disposable Git repositories, package
copies, caches and full source snapshots are excluded from this evidence commit.

Independent reviewer `estate-a3425ebf9874/remote_estate` inspected the complete
two-expression production delta and ran two distinct actual-Git consumers. Both
fail on the original source and pass on the frozen candidate. The controls cover
header-shaped Unicode payloads, two changed files, a decorated async method,
no newline at EOF, and pure-deletion anchors with both branches executed. The
unchanged driver, logs and source-pinned receipt are under `independent/`. No
remaining scoped defect was reported; the 78 author cases were not repeated. Public commit metadata may differ from
native commits when the supported GitHub API creates the final actual-parent
composition; any mapping and source/tree verification belongs in a separate
publication receipt.

## Language contract

Python's lexical reference defines physical lines using LF, CRLF or CR:
https://docs.python.org/3/reference/lexical_analysis.html#physical-lines

Python's string reference documents the additional boundaries recognized by
`str.splitlines()`:
https://docs.python.org/3/library/stdtypes.html#str.splitlines

The wider string-splitting behavior is useful for generic text but does not
preserve Git hunk counters or Python AST physical-line positions.

Raw pytest failure captures and unified patches intentionally retain their exact
whitespace. Their trailing-space diagnostics are evidence bytes, not source
formatting changes. Authored source, scripts, Markdown and JSON pass the normal
Git whitespace check; no commit hook or repository gate was disabled.
