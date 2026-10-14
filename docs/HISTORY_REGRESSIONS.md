# Find saved paired-regression results

The existing `history` command can now include saved `testpilot.regression/1`
records. This reads saved files only: it does not rerun their tests, contact a
model, inspect Git, or open any repository, interpreter, test or artifact path
named inside a record.

From a source checkout with Python 3.12 or newer:

```sh
python -B -m testpilot history --root /path/to/saved-results --include-regressions
python -B -m testpilot history --root /path/to/saved-results --kind regression --json
```

`--include-regressions` adds the exact filename `regression.json` to the existing
`report.json` and `recheck.json` candidates. `--kind regression` also enables
that discovery and selects regression rows. The schema inside a selected file
determines its kind. Existing generation/recheck commands and default discovery
are unchanged when both options are omitted.

The API is `scan_history(root, *, include_regressions=False, kind=None, ...)`.
The inclusion flag must be a Boolean. An explicit `False` preserves default
discovery unless `kind="regression"` explicitly selects regressions. Opted-in
results include `filters.include_regressions: true`; default results retain their
existing keys and values.

## Read the recorded comparison

Each regression row keeps the selected file's relative path, exact byte count
and SHA-256, recorded status and retained test path labels. Its
`regression_context` contains separate `before` and `after` objects with recorded
requested refs, commits, trees, snapshot hashes, source file/byte counts and
native result summaries. There is no combined `final` execution.

The comparison object reports recorded `comparable` and `reason` values and the
lengths of the witness, paired-case and unmatched-case arrays. These are saved
claims, not a freshly verified verdict. A recorded `verified_regression` status
does not make history an independent regression verifier. Test bodies and native
diagnostic output are not displayed. Context paths and identifiers are literal
labels; they are neither followed nor reconciled with current source.

For example, the two retained cross-product records used to receive this feature
record local fixture commits `968723943b234fee81b1d2ee644fa95038313c64` before and
`a95c709541755cefbcad2b462b9284692b33436a` after, with one witness and two paired
cases. Their overall native counts are two passes/one failure before and three
passes after, including an unchanged smoke test. The separate retained-test
counts are one pass/one failure before and two passes after. Historical upstream
CaptureSuite source identities are a separate provenance mapping, not substitutes
for these local fixture commits.

## Scope, filters and errors

The default depth is one; `--max-depth` accepts zero through eight. Existing
status filters are ORed, and the optional case-insensitive query must also match
a relative report path, target label or retained test path. Queries do not search
recorded source, diagnostics, repository paths or commit identities. Rows remain
sorted by relative report path, not by inferred chronology.

Regressions share the same limits as other candidates: 1,000 candidate files,
20,000 directory entries, 16 MiB per file and 64 MiB total reads. Internal
symlinks are skipped. Selected reports must be regular files; nonregular files
are not consumed. Strict finite UTF-8 JSON admission, duplicate-key refusal,
console handling and partial-result behavior are inherited from history.

Unknown schemas, malformed core records and read/limit failures appear as
problems alongside admitted rows; filters do not hide them. Opted-in invalid-core diagnostics name all three supported kinds; default
diagnostic bytes remain unchanged.

Exit status 0 means complete within the selected scope, including no matches;
1 means a partial listing with problems; 2 means invalid options/root or failed
console delivery. Discovery is not an atomic filesystem snapshot or proof that
every result anywhere has been found.

## Verification and provenance

The focused course covers opt-in discovery, both exact historical reports,
separate phase identities, literal statuses, filters/depth/shared budgets,
inert recorded paths, nonregular/link handling and actual CLI output. The
unchanged history tests cover the existing generation/recheck contract.

An initial candidate's malformed list/object status escaped as `TypeError`.
The retained witness and beforeimage remain in receiving evidence; the final
source checks that status is text before checking the supported status set.
Fifteen final focused methods and 21 unchanged history methods pass. The earlier
14-method candidate result is historical, and the baseline negative course is
not relabeled as a final-source run.

This is issue 129's bounded follow-on to the original finder in issue 39. Only
`testpilot/history.py` and the history subparser in `testpilot/__main__.py`
change existing code. The regression producer and original history guide/tests
remain unchanged. These results qualify saved-file discovery, not model, native
test, Windows, scientific or historical regression re-execution.
