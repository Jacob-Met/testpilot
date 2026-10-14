# Compare two saved TestPilot runs

Use two existing report files to make a portable review page:

~~~bash
python -m testpilot compare \
  --before out/before/report.json \
  --after out/after/report.json \
  --out comparison.html
~~~

Open the HTML directly in a browser. The command consumes saved reports and writes one new file. It does not call a model, run pytest, apply a patch, inspect a working repository, or recompute prices. Comparison needs only Python 3.12+ and TestPilot's source; pytest, coverage, provider credentials, a server, and a network connection are not needed.

The output path must be new, and its parent directory must already exist. Existing output files and aliases of either input are refused. TestPilot first reads and validates both reports, renders the complete page, and stages it beside the requested output. It then publishes the completed bytes without replacing an existing path. A filesystem that cannot create a hard link in that directory refuses publication. Exit code 0 means the page was written and its success message was delivered to stdout. Exit code 2 means the inputs, arguments, or output destination were refused, or console delivery failed. The original inputs are never rewritten.

If console delivery fails after publication, the complete comparison remains at the selected output path. When stderr is writable, the diagnostic says that the comparison was written but console delivery failed. A closed or unencodable diagnostic stream can prevent that message; the command still returns 2. A console destination may already have received partial text. Check the selected output before retrying, because an occupied path remains protected.

Cleanup of the private `.testpilot-compare-*.html` stage is best effort. A filesystem error removing that stage does not undo successful publication or replace an earlier write/publication error. The private stage may remain beside the output when removal fails; an already-published page still has its complete bytes. Other cleanup exceptions, including interruption, remain visible.

To locate saved inputs first, use the [saved-run finder](HISTORY.md#compare-two-selected-generation-reports)
with `--kind generation`. Choose the Before and After roles explicitly; finder
order does not establish chronology. History's core-record admission and larger
per-file bound differ from comparison's full input contract below, so discovery
does not guarantee that a report is a valid comparison input. Conversely, a
comparison-admissible report may fail history's core-record requirements.
See the [runnable fictional walkthrough](../examples/saved-review/README.md).

## What the page shows

| Section | Meaning |
|---|---|
| Recorded results | Each input's status, selected-target count, retained generated files, reported tests written, repair-round budget, JUnit availability, and recorded suite/generated-case counts. |
| Selected-source context | Exact recorded path and qualified-name grouping, source text, line range, and changed lines from each report. Duplicate labels remain separate records. |
| Generated-file changes | Added, removed, changed, or unchanged saved source strings by exact path, with a textual diff and complete retained source. Empty files remain distinct from absent files. |
| Final diagnostics | Each report's run message, native final summary, individual case outcomes and generated-file attribution, diagnostics, and saved pytest output tail. |
| Recorded coverage | Each original run's before-generation and after-generation measurements and its own reported delta. |
| Recorded usage | Each original total, token estimate flag, cost-completeness flag, and ordered call ledger. |
| Saved rounds | Original generation/repair round labels, files, warnings, and result summaries. A model-only reply stays a round without a test result. |
| Original reports | Source filenames, byte lengths, SHA256 identities, and two exact original JSON downloads. |

Before and After are roles supplied by the command. They do not authenticate chronology. Matching target labels identify matching saved path/name fields; they do not establish an identical repository, commit, environment, test selection, or test implementation. A renamed path remains an addition/removal, and identical case names are not treated as proof of equivalent tests.

The page displays recorded outcomes without adding a claim of improvement, correctness, or model quality. It does not calculate a pass-rate change or compare coverage percentages across different source denominators. Coverage deltas shown in the page belong to their individual original runs.

When a report lacks complete JUnit evidence, suite and generated execution counts remain unavailable. The reported tests-written value may count authored definitions without proving any execution. Missing coverage remains unavailable. Incomplete pricing remains unpriced even if a partial numeric cost was recorded. The comparison neither fills missing measurements with zero nor estimates a missing price.

## Offline interaction and exact downloads

Section links, native expandable panels, keyboard focus, horizontally scrollable source/table regions, and download links work without JavaScript. At narrow widths the two report panels stack. Use the browser's Print command for a paper or PDF view.

Recorded failed and error cases start expanded in each report's Final diagnostics panel, including cases with no diagnostic text. Passed and skipped cases and the saved pytest output tail start collapsed. Use each native disclosure to collapse or reopen it with a pointer or keyboard. This reading state does not change the recorded outcome or make missing JUnit evidence complete.

When either report retains failed or error cases, **Failed and error cases** at the start of Final diagnostics links directly to each matching occurrence. The link names its Before/After role, one-based position in that report's retained case array, outcome and literal case label. Repeated labels have separate targets; a position is not a cross-report test identity. The count describes retained rows, not unique tests or complete execution. Reports with no matching rows add no index, and missing final/JUnit evidence keeps its existing meaning.

Activate a link with a pointer or native keyboard navigation to move to the corresponding disclosure, which receives a visible target outline. Use its summary to collapse or reopen it. These links do not filter or rewrite the report, and all case rows remain in their original order. The index is hidden in the print view while the existing full diagnostics remain available. The original JSON downloads carry no reading position or disclosure state.

Both JSON downloads preserve all original bytes, including a UTF-8 byte-order mark, whitespace, line endings, additional fields, and original number spellings. The page does not regenerate downloaded JSON from its parsed view. Role-specific download filenames are before-report.json and after-report.json.

Report text is rendered literally. HTML markup cannot create page elements or request external content. Control characters, Unicode line/paragraph separators, and unpaired surrogate characters use visible escapes in the review view. Downloads preserve their original JSON bytes. The self-contained page has no executable scripts, external assets, or browser storage.

## Supported input contract and bounds

The consumer accepts native TestPilot LoopResult.to_dict() reports containing the recorded status, targets, generated files, definition count, round budget, final result, coverage, ledger, rounds, plan, message, and patch. Older native reports without a JUnit-availability flag or generated-case attribution can be reviewed, with that execution evidence labeled unavailable. Unknown extra fields are retained in original downloads and must still satisfy the general JSON bounds.

Admission is strict: JSON must be UTF-8 (an initial BOM is accepted), have one object root, and have no duplicate object fields or non-finite numeric constants. Consumed strings, booleans, arrays, counts, line ranges, outcome labels, coverage ranges, and nested result/ledger shapes must have native types. Boolean values do not count as integers. Numeric text is parsed with decimal precision, so a tiny finite value is not silently rounded to zero.

| Bound | Limit |
|---|---|
| Each input | 4 MiB; regular saved files only |
| Parsed values | 200,000 nodes and at most 64 levels of nesting |
| General arrays/objects | 20,000 entries |
| Selected targets / saved rounds | 2,000 each |
| Retained generated files per source snapshot | 500 |
| Numeric magnitude | At most 2**53 - 1; applicable counts are nonnegative |
| Fractional/exponent number spelling | 128 characters |
| Inline diff | At most 200,000 combined source characters and 2,000 physical LF-delimited lines per side |

Above the inline-diff threshold, the page explicitly omits only that diff; complete saved source and both original JSON downloads remain available. Input/schema limits are refusals, not partial reports. The view validates supported representation, not the truth of a report's claims or the internal arithmetic of producer totals.

## Validation

The focused tests exercise exact original bytes, deeply immutable parsed inputs, missing evidence, Decimal precision, differing/duplicate target labels, added empty files, source-line edge cases, malformed and bounded admission, no-overwrite publication, staged-write failures, special-file refusal, and a consumer-only CLI path:

~~~bash
python -m pytest -q tests/test_compare.py tests/test_compare_cli.py tests/test_compare_cleanup.py tests/test_compare_console.py tests/test_compare_diagnostics.py tests/test_compare_case_index.py
~~~

Native receiving evidence for this contribution, including actual scripted runs, the missing-command baseline, literal changed-input checks, offline-browser downloads, phone-layout regression, and source hashes, is recorded in docs/receiving/saved-run-comparison-490fcd7c4056/.

The initial diagnostic disclosure change has separate [original-first source and browser receiving](receiving/comparison-diagnostics-dcac8b3b8755/README.md), including preserved observer failures and exact fictional reading copies.
