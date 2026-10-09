# Inspect saved added-line coverage

Use the coverage-gap reader when a TestPilot report gives an aggregate percentage
but you need to identify the exact changed lines that remain missing in its
retained final run. The reader works entirely from a saved report. It does not
open a repository, execute recorded source or tests, invoke a model, install
dependencies, or change that report.

From a project checkout using its configured Python 3.12 or later:

```sh
python3 -B -m testpilot.coverage_gaps --report saved/report.json --output gaps.json
```

The output parent must already exist and the output path must be new. Omitting
`--output` writes the same UTF-8 JSON bytes to stdout. Both destinations use LF
line endings, including on Windows, so publication preserves the checked byte
limit. An existing file or symlink, including
the input report itself, is refused. Invalid report metadata is rejected before
output creation. An actual output I/O failure stays nonzero; partial output after
such a failure is not promised to be rolled back.

The JSON lists files and their added line numbers, with the original function
ordinals that mention each line. File labels join the coverage mapping by exact
recorded text: `calc.py`, `Calc.py`, `./calc.py` and slash variants are distinct
labels. Labels are never interpreted as paths to open. Unicode, backslashes and
other literal label characters survive as JSON data.

Each line has one of four states:

- `executed`: present in the retained final coverage file's executed array.
- `missing`: present in its missing array.
- `not_represented`: absent from both retained arrays, or the file label is absent.
- `unknown`: final coverage was not retained.

A line marked `not_represented` is not demonstrated to be non-executable, excluded,
filtered, covered, or safe to ignore. The saved report lacks the evidence to
choose among those explanations. Missing or null final coverage is unavailable;
a present but malformed coverage structure is rejected. A line declared both
executed and missing is also rejected.

The summary counts each exact file/line pair once, even if repeated or associated
with several functions. Its known-executable count and percentage concern only
changed lines present in retained executed or missing sets. They are not overall
project coverage and do not establish coverage for unrepresented lines.
Unavailable counts and zero-population percentages are null. Unknown lines are
separate from missing lines.

TestPilot's recorded `changed_lines` are added new-side lines inside a touched
function, not every line in that function. A pure-deletion or unchanged explicit
target may therefore have an empty changed-line list. Such function records stay
in the result in their original ordinal order. Files with no changed lines do
not acquire an artificial line population. Only final coverage is inspected;
earlier rounds and aggregate percentages do not override it.

Input is limited to 8 MiB, 4,096 functions and coverage files, 4,096 characters per
label, and 100,000 total raw entries across changed-line and retained coverage
arrays. Entry limits are checked before deduplication or association expansion.
Output is limited to 16 MiB before publication. Duplicate JSON object keys,
nonfinite JSON constants, boolean/nonpositive/noninteger line numbers, and
changed lines outside their recorded function span are rejected.

The focused fixture under `tests/fixtures/coverage_gaps_report.json` is authored
synthetic reader evidence. Its coverage arrays do not claim a real pytest or
model execution. This additive module does not change the existing coverage
collector, aggregate report, comparison, recheck, exported tests, source selector,
configured interpreter floor, or their separate source and integration owners.

The active Python integer-conversion limit remains unchanged. JSON integer
conversion or result serialization that exceeds it produces an explicit reader
error; this command does not disable or raise that runtime limit.
