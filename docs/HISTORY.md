# Find saved TestPilot runs

Use `history` to find generation and recheck reports already saved beneath a
directory. It reads the reports and prints their recorded outcomes, target
labels, retained test paths and provenance. It does not run tests, construct a
model, execute saved code, apply a patch or open paths recorded inside a report.

From a TestPilot checkout with Python 3.12+:

```sh
python -B -m testpilot history --root eval/results
python -B -m testpilot history --root /absolute/path/to/saved-runs --max-depth 3
python -B -m testpilot history --root /absolute/path/to/saved-runs --status failed --status suspected_code_bug
python -B -m testpilot history --root /absolute/path/to/saved-runs --query 'Parser.parse' --json
python -B -m testpilot history --root /absolute/path/to/saved-runs --kind recheck
```

Choose a root that contains saved `report.json` or `recheck.json` files. The root
is required. Its files have depth 0; the default maximum depth of 1 also includes
immediate subdirectories. `--max-depth` accepts 0 through 8. Results are sorted
by relative path, not by a timestamp or presumed execution order. An explicitly
selected root symlink may resolve to a directory; links encountered inside the
root are skipped, including links with report filenames. Hard-linked regular
files at different paths remain different rows.

## Read the result before using a saved report

Each row identifies its relative path, record kind, byte length and SHA256 of
the bytes actually read. A generation row lists its recorded function path and
qualified name. Both kinds list retained test paths and the recorded final
summary/counts. Recheck rows also preserve the recorded repository, interpreter,
timestamp labels and source-report path/hash/status. These are literal saved
claims. The finder does not authenticate their producer, compare those hashes
with current files, parse their timestamp labels, or reconcile all nested
diagnostics.

Missing historical `final.junit_available` is shown as `null`. It is not turned
into `false`, a verified execution count or a new pass/fail conclusion. A
historical failure does not itself authorize replay or patch application.

Text output escapes control characters and Unicode labels as JSON strings.
It omits saved source, patch, test bodies and runner output. `--json` prints the
complete `testpilot.history/1` result as ASCII-safe, sorted, indented JSON with
one trailing newline. Every row and problem remains available in that result.
Redirect only to a distinct output path: shell redirection happens before this
command starts and could truncate a report if you choose that report as output.

## Filters select rows; problems remain visible

Repeated `--status` arguments are exact-string alternatives. Their order and
repetitions remain in the result's filter description; an unknown label is a
valid filter that may match nothing. Different filters are combined with AND.

`--query` is a casefolded literal substring of the relative report path, target
path, qualified function name or retained test path. It is not a regular
expression and does not search source bodies, runner diagnostics, status labels
or a recheck's recorded source-report path. Empty query text matches every
admitted row. `--kind` selects `generation` or `recheck`.

Every candidate is structurally admitted before filters apply. A malformed
neighbor still makes the scan partial even when it would not match your filter.
Filenames only discover candidates: the admitted schema determines record kind.
A generation-shaped `recheck.json` is reported as generation.

## Complete and partial scans

| Exit | Meaning |
| --- | --- |
| 0 | The selected root/depth was scanned completely within the limits, including a valid search with no matching rows. |
| 1 | One or more problems made the scan partial. The available rows and every problem are printed. |
| 2 | Options/root could not be admitted, or stdout delivery failed. A failed output may contain a partial rendering; it is not retried. |

`complete` is true exactly when the result has no problems. Choosing a shallower
depth intentionally excludes deeper directories and does not itself make the
selected scope partial. Missing, unreadable or structurally invalid candidates
are explicit problems; healthy admitted siblings remain useful.

The scanner only accepts regular report files. It rejects duplicate JSON keys,
NaN/Infinity/nonfinite floats, invalid UTF-8/JSON and native parser limits. It
accepts an optional UTF-8 BOM. The known native generation or recheck core must
have the expected types; booleans do not count as integers. Additional fields
are allowed. This is bounded structural admission, not full semantic validation
or renewed verification of recorded tests.

The fixed work limits are:

| Limit | Behavior when exceeded |
| --- | --- |
| 1,000 candidate files | Stop before considering the next candidate; emit `candidate_limit` at that path. |
| 20,000 directory entries | Discard that directory's collected list, emit `entry_limit` and stop. No arbitrary filesystem-order prefix of that directory is selected. |
| 16 MiB per report | Emit `report_bytes_limit`, without reading its body, and continue to later siblings. |
| 64 MiB total report-body reads | Stop before reading an otherwise size-admissible candidate that exceeds the remaining allowance; emit `total_bytes_limit`. |

Type and per-file size admission happen before the remaining global-byte check.
A file larger than 16 MiB therefore produces `report_bytes_limit` and scanning
continues even if that size also exceeds the remaining total allowance. Exact
byte-boundary files can be admitted. Invalid captured bodies still consume the
global byte allowance. Filters never reduce discovery or admission work.

Directory entries are counted, then sorted by their exact Python string names
before depth-first traversal. Entry overflow may observe one extra sentinel,
but `entries_seen` stays at 20,000. An enumeration error discards that directory's
partial list and continues other admitted siblings. The candidate count includes
type/per-file/JSON/schema errors and the candidate that hits `total_bytes_limit`;
it excludes only the overflow file refused by `candidate_limit`. `bytes_read`
counts acquired report-body bytes, `admitted` counts structurally accepted rows
before filtering, and `matched` counts returned rows.

Reads are bounded and descriptor sizes are compared before/after capture. A
size change or incomplete capture is `read_error`. Stop writers when you need
a stable view: these checks do not provide a concurrent-writer snapshot or a
hostile-path security boundary. Report paths are labels, not chronology.

## Python API

```python
from testpilot.history import HistoryError, scan_history

try:
    result = scan_history("/absolute/path/to/saved-runs", max_depth=2,
                          statuses=("failed", "no_tests"), query="parser",
                          kind=None)
except HistoryError as error:
    print(error)  # invalid options or explicit root; no scan result
else:
    print(result["complete"], result["runs"], result["problems"])
```

`root` accepts a string or `Path`. `max_depth` must be an integer from 0 through
8 (not a boolean), `statuses` a list/tuple of strings, `query` a string or `None`,
and `kind` `generation`, `recheck` or `None`. Options are checked before filesystem
access. The API prints nothing and makes no project or report changes.

This implements the saved-run finder requested in issue 39, retaining the
original proposed scope and source-integration ownership credit. Other commands
keep their existing behavior. To recheck a deliberately selected saved report,
consult the separate [recheck guide](RECHECK.md); finding it is not a replay.
