# Function-line selection qualification

This contribution indexes the native selector's integer line sets once per
Python source file. It preserves complete target records while reducing repeated
line scans for dense edits in files with many functions. Ownership is recorded
in [issue #79](https://github.com/Jacob-Met/testpilot/issues/79).

## Exact source and scope

- First measured parent: `8e9c0d3ab67e376a94c06acab04877d265f959df`.
- Current parent: `52275f50e672c145d8f69e90cf40948ab28a7d79`.
- Local source qualification commit: `e0605702c37a17cf7d8ae92385fe17c546da6a72`.
- Original selector SHA-256: `33e97c96d67b263b5dd8116e22f3528ecb717576c6304506c8da728fceb0f0ff`.
- Candidate selector SHA-256: `60255ce91ded605323ad6d58608ba4681c7c70a1478f1e6da9e89a7675034977`.

The current parent adds the separately owned coverage-probe timeout. Its selector
and workflow are byte-identical to the first measured parent. The candidate was
rebased onto that current parent before the complete candidate suite and final
benchmark. All three coverage-probe paths are preserved.

[source-scope.json](source-scope.json) records the source, maintained-test,
benchmark and workflow identities. All 1,515 inherited leaf bytes and modes were
compared against the current parent: only `testpilot/diff.py` differs. Within that
file, the change is the standard-library bisect import and the line lookup in
`functions_touching`. The parser, AST discovery, source decoding and extraction,
automatic traversal and explicit target resolution remain unchanged.

The new maintained regression and benchmark were authored before the production
edit. The six regression cases passed against the original selector first.
Because this is an optimization, those retained-behavior cases are expected to
pass on both versions; the measured difference is execution cost.

## Maintained verification

Environment: Linux, CPython 3.12.14, pytest 9.1.1 and coverage 7.16.2, in a
disposable virtual environment. No model/provider calls were made by the new
regressions or benchmark.

| Check | Result |
| --- | --- |
| New complete-record cases on original selector | 6 passed |
| Candidate selector/explicit-target/CLI closure | 41 passed, 6 subtests passed |
| Candidate source/path/hunk boundaries | 110 passed |
| Original complete suite, first measured parent | 538 passed, 33 subtests passed, 2 failed |
| Candidate complete suite, current parent | 549 passed, 33 subtests passed, 2 failed |

The additional 11 passing cases in the complete candidate result are the
current parent's five coverage-probe cases and this contribution's six cases.
Both complete runs fail the same existing parameterized tests:

- `test_interrupt_does_not_drain_a_detached_helpers_pipe[escape-wait]`
- `test_interrupt_does_not_drain_a_detached_helpers_pipe[escape-exit]`

Both failures assert that a detached child remains running after interrupting
the fixture's leader; this environment observes `child_running == False`.
A separate [owned-process observation](process-observation.json) confirms a
limitation in the tests' process lookup here: after an owned worker printed its
readiness marker, `Popen.poll()` still saw it live before and after the exact
`ps` query used by the tests, but the returned command record did not contain
that worker's path. The maintained path-based ownership predicate therefore
cannot reliably identify that live process in this environment. This is
consistent with the failures; it does not qualify actual detached-process
cleanup. This contribution does not alter `_run` or those tests, and neither
complete suite is reported as fully passing. The complete logs are retained
beside this document. The diagnostic's own worker was terminated and reaped.

The maintained cases compare literal expected records for decorators, async and
class methods, nested attribution, repeated qualified names, exact boundaries,
empty and deletion-only selections, out-of-range integers and syntax errors.
They exercise LF, CRLF and CR physical lines while preserving U+2028 inside a
Python string. A real `targets --json` process receives a 160-function new file
and must return every complete expected record in order without altering it.

## Complete CLI measurements

The [reproducer](benchmark.py) builds identical fictional sources and diffs,
then runs the actual `python -B -m testpilot targets --json` child in each source
checkout. Seven before/after pairs alternate order for each fixture. Every
result must match literal fixture expectations and the first complete stdout
byte sequence; exit status must be zero and stderr empty. Source and input
hashes are checked after the trials.

Each measurement includes process startup, imports, diff/file reading, AST
selection, JSON serialization and captured output. The dense fixture is a new
6,000-line source containing 2,000 functions. The sparse fixture has the same
function count with every hundredth return edited. The small fixture is a new
five-function file.

| Fixture | Initial before → candidate median | Matched-current-parent before → candidate median |
| --- | --- | --- |
| Small new file | 74.232 → 78.996 ms | 181.311 → 163.758 ms |
| Dense new file | 750.063 → 163.970 ms | 1,355.072 → 311.209 ms |
| Sparse edits | 96.154 → 112.539 ms | 205.825 → 138.927 ms |

The [initial series](benchmark-concurrent.json) overlapped other qualification
work and used the first measured parent. The [final series](benchmark.json)
uses the matched current parent after this lane's suites completed. This is a
shared runner, so neither series establishes isolated-host throughput. The dense
case improves in both series; the small and sparse results vary and support no
general speedup claim. Both series preserve every complete output byte across
all 84 actual CLI children, with source and fixture bytes unchanged.

The implementation adds two temporary lists containing references to the input
line integers. It does not reduce AST storage, file reading, serialized output,
model latency or pytest execution cost. Memory use was not benchmarked.

## Independent receiving

The separate `context_adoption` worker reviewed the original selector and CLI
contract, then froze independently authored fixtures and complete original
outputs before reading the candidate or its maintained tests. Its
[receipt](independent-receipt.json) accepts the same candidate selector SHA-256.
All 176 API cases match the original, including 168 cases checked against literal
complete expected records. Eight actual CLI invocations per source also preserve
exact stdout, stderr and exit bytes, with all source inputs unchanged.

The receiver includes LF/CRLF/CR, decorators, async methods, nested ownership,
repeated qualified names, try/finally/handler and match discovery, U+2028 literals,
empty and large integer sets, deletion anchors, class-header-only changes and
saved-diff/stdin CLI intake. It does not repeat the full suite or claim installed
behavior or general performance.

The first independent oracle assumed exception handlers precede `finally`
definitions. Original-only execution disproved that assumption. The receiver
corrected its literal order to match the unchanged original and froze a new
packet before candidate exposure; no production correction was needed. The
rejected first freeze, correction note, final fixtures, original/candidate
outputs and exact [receiver](independent-receiver.py) are retained in the
[receiving archive](independent-receiving.tar.gz). Its complete member hashes and
archive SHA-256 are recorded in [independent-archive.json](independent-archive.json).

To reproduce from two existing source checkouts:

```sh
python -B benchmark.py \
  --before /path/to/parent-checkout \
  --after /path/to/candidate-checkout \
  --output /path/to/new-measurements.json
```

## Publication boundary

The unchanged workflow blob is
`86a3236e38155506b5fe6077322d508f7f676649`. Its only subscriptions are pushes to
`main` and pull requests. Rulesets read back as empty, and main reports no branch
protection. The connector does not support the workflow-registry collection;
the complete Git tree and actual workflow source provide the trigger evidence.

Source publication is limited to an isolated feature branch carrying skip
directives. No pull request, main update, Actions dispatch, workflow/settings
change, provider request or installed-runtime adoption is part of this delivery.
Independent source review and any native receiving are recorded separately from
the authored results above.
