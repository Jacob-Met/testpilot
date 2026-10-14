# Discover and compare saved runs

This small fictional example connects the saved-run finder to the portable
comparison page. It needs Python 3.12+ and this TestPilot checkout. Neither
command runs the tests, source strings or patch retained inside a report.

## Find the two inputs

From the repository root:

```sh
python -B -m testpilot history --root examples/saved-review/saved-runs --kind generation --max-depth 1
```

The two rows are `after/report.json` and `before/report.json`. History sorts
paths; it does not establish chronology. Both rows contain invented recorded
failures. Their labels do not mean that a test ran during this walkthrough.

## Assign roles and make a new comparison

```sh
python -B -m testpilot compare --before examples/saved-review/saved-runs/before/report.json --after examples/saved-review/saved-runs/after/report.json --out comparison.html
```

Use a new output filename if `comparison.html` already exists. Its parent
directory must exist. Open the resulting HTML directly in a browser.

Follow **Final diagnostics**, then **Failed and error cases**. The six links
identify retained occurrences by Before/After role and their original positions.
Repeated labels have different targets. Native disclosures let you inspect or
collapse each diagnostic. Missing complete JUnit evidence stays unavailable.
Both original JSON download links retain the exact bytes of these two inputs.

Use `--json` on the history command when you need paths, hashes and problems in
machine-readable form. Its `complete` flag describes the selected root, depth
and work limits; a recorded failure does not make discovery incomplete.

## What these fixtures represent

These are new fictional derivatives of the comparison-index receiving fixtures.
The only semantic addition is `final.coverage: null`, followed by UTF-8/LF JSON
serialization. The native `SandboxResult.to_dict()` producer includes that field.
No recorded test outcome, source string or diagnostic was recomputed.

The earlier comparison fixtures were valid for `compare` but were refused by
`history` because they omitted this native core field. That failed trial remains
in the [receiving record](../../docs/receiving/history-comparison-dcac8b3b8755/README.md).
The original comparison-index inputs and artifact remain unchanged.

History and comparison have separate admission contracts and limits. Passing
either command does not promise acceptance by the other. Recheck records have a
different schema and are not comparison inputs. Consult the [history guide](../../docs/HISTORY.md)
and [comparison guide](../../docs/COMPARE.md) for real saved reports.

The actual walkthrough used the adopted 16-module CLI closure on CPython 3.12.14.
History found both generation inputs; comparison produced six unique occurrence
targets and embedded both exact derivative originals. This walkthrough adds no
new browser, print or screen-reader qualification.
