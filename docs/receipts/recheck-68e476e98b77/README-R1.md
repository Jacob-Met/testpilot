# Saved-test recheck receiving — 2026-10-08

## Product outcome

After fixing application code, a caller can run `python -m testpilot recheck`
against the exact generated tests in a retained report, without another model
call. The original report and checked project remain unchanged. Current results
are written to a new directory as `recheck.json` and `recheck.md`.

Product instructions: [RECHECK.md](../../RECHECK.md).

## Exact source

- Repository: `Jacob-Met/testpilot`.
- Original discovery and unchanged CLI baseline: commit
  `05aab727498df2af27dc6fff17d9375d76c57900`, tree
  `be8dcf0683a5a9374f67c4b94437fa37c67d484e`.
- Qualified current receiving parent: `3e745e6b6a2f7e383fc6b43f12e69f7a221fb051`,
  tree `56b8c198f3d88e133c6d641b0cc7c63de0dd6fcd`.
- Frozen five-path product tree, before adding this evidence directory:
  `613172af8541a262c9af9039669b97d58e576967`.
- `source-binding.json` records every changed blob and all 23 materialized
  current inputs. The original full parent tree was reconstructed first;
  all 726 unowned parent leaves are preserved in the product composition.

The existing CLI gains an additive parser/dispatch. The new recheck module
admits bounded retained JSON and validates exact path/content placement.
`run_pytest` gains an opt-in `exact_files` mode: new retained files use binary
UTF-8 output and matching copied regular files are accepted without rewriting.
Its default text-write path, collector, subprocess timeout, environment and
interpreter behavior remain unchanged. The accepted upstream PR10 model blob
`6d4abca38cc1c256df00bcac7923e2dc0bd42b16` is preserved exactly.

## Original evidence and correction

The unchanged original CLI produced the maintained calc_clamp report with
status `suspected_code_bug`: three failed and one passed generated case, and
three deterministic ScriptedModel calls. Its absent recheck command returned
argparse exit 2 without output. `original-generated-report.json` has SHA-256
`0761bedf94965d7e8a3bfac072b5f0c3f50b854494821712c23f11f1c0fa82d2`.

The first implemented candidate passed 32 focused cases and failed one:
an already-applied mode0444 test could not be rewritten in the private copy.
`initial-focused-tests.stdout` preserves that actual EACCES traceback.
The initial module and regression source are retained as text alongside their
exact recorded hashes; this result is not relabeled as a final success.

The opt-in retained-byte seam fixes that failure and avoids text newline
translation for new retained tests. Original generation still uses its
unchanged default write behavior. The ownership scope extension was accepted
by the integration lead after a fresh current-owner read.

## Native qualification

Native platform: ordinary UID1000 on Linux, Python 3.14.4, pytest 9.0.2.
No dependencies were installed. The selected project venv has no pip and
reuses existing system test tooling.

One current-source focused command:

```sh
python3 -m pytest -q -p no:cacheprovider \
  tests/test_recheck.py tests/test_cli_python.py \
  tests/test_cli_targets.py tests/test_sandbox.py
```

Result: **57 passed, 6 subtests passed, 1 skipped**, in 35.04 seconds.
The sole skip is the existing optional coverage test (`coverage not installed`).
All 33 new recheck cases pass. This is not a full repository/eval suite result.
The raw command, source pins, stdout and stderr hashes are retained.

The separate unchanged real-report receiver passes ten actual recheck controls:

| Control | Exit | Current result |
| --- | --- | --- |
| Original buggy Git checkout | 1 | Three retained cases fail, one passes |
| Maintained fixed Git checkout | 0 | All four retained cases pass |
| Exact already-applied mode0444 tests | 0 | Four cases collected once; no rewrite |
| Different current test bytes | 2 | Refused before pytest/output |
| Previous recheck.json used as input | 0 | Same exact retained tests pass |
| Current existing-suite regression | 1 | Failure retained despite four generated passes |
| Helper-only saved content | 1 | no_tests; existing passes do not qualify it |
| Saved blocking test | 1 | Native timeout record and bounded cleanup |
| Default Python missing project-only dependency | 1 | Import failure recorded |
| Selected prepared project Python | 0 | Four retained passes; actual prefix/executable verified |

`consumer-receipt.json` records all ten controls and eighteen native commands
(including Git and venv setup), exact report/test/checkout hashes, and source
pins before and after. Every actual recheck used an invalid
`TESTPILOT_BACKEND` tripwire; none constructs a model. Original report and
checkout bytes stayed unchanged. Recheck results retain zero new model calls.
The original generation's three scripted calls remain separately attributed.

## Scope and preserved limitations

The current collector is reused. Its owners' PR22 (fence/patch) and PR23
(native collection across pytest versions) remain independent contributions.
The native pytest9.0.2 results here do not claim to resolve their separately
reported pytest8 or pytest9.1.1 cases. A later incoming-main composition must
preserve accepted owner changes and bind its own full tree.

Recheck runs the normal process-level sandbox, not a new security boundary.
No provider call, installed-runtime activation, Windows execution, historical
coverage comparison, patch application or whole-project isolation guarantee
is claimed. Hosted CI and final public integration are separate later records.

Two capacity preflights stopped before any receiver fixture/output or product
execution because shared free space was below 128 MiB. The unchanged receiver
resumed after its own measured guard cleared. The lead's separate completed
compiler-cache retirement was on a different filesystem and does not establish
or explain the TestPilot home-volume recovery; see the capacity sidecar. Smaller tooling preflight failures (E2BIG
before spawn and a missing new docs directory before pytest) are recorded
separately and are not presented as product outcomes.

## Custody and replay

The complete original/final native source, stdout/stderr, receiving checkouts
and driver remain under `/home/jacob/testpilot-recheck-68e476e98b77`.
This directory contains the compact immutable source/result packet. Native
paths in historical JSON identify actual execution; they are not portable
installation defaults.

To repeat the useful developer workflow elsewhere, use the maintained
`eval/cases/calc_clamp/repo` and `eval/cases/calc_clamp/fix/calc.py` from the
cited original source, keep this original report unchanged, and invoke
`testpilot recheck` first against the buggy checkout and then the fixed one.
Use distinct output directories outside each checkout. The retained native
driver is included verbatim for audit; its explicit ROOT path and source-pin
checks refer to that historical receiving layout.
