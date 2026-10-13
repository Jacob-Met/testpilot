# Saved comparison console delivery — dcac8b3b8755

Source parent: `b751e1cff2b7902bbebd6e7040f764d49bcb1a46`.
Coordination: [TestPilot issue 98](https://github.com/Jacob-Met/testpilot/issues/98).

## Outcome and scope

The comparison command now uses the existing console writer for its success message and error diagnostic. A failed write or flush returns status 2. If the HTML was already published, it remains complete at the requested path and a writable stderr receives:

```text
testpilot: comparison was written, but console delivery failed
```

The change is confined to the compare dispatch block in `testpilot/__main__.py`, seven focused regression cases in `tests/test_compare_console.py`, and the console/exit notes in `docs/COMPARE.md`. The local helper import leaves the separate targets-preview scope unchanged. The existing console helper, comparison admission, rendering, exclusive publisher and every other command remain unchanged.

Candidate product blob: `76b09d5a1e55780efc78a2b48f0b3fae162da196`.
New regression blob: `5555f2073d480d3fb46227550442f2d0ecca3673`.
Guide blob: `6ba41eced0e47dd81fc6b4565a054fcdd1e66a59`.

## Actual native receiving

The author used Linux / CPython 3.14.4 and an isolated 19-file original-source projection. Every projected original was checked against its published Git blob before execution. The candidate changes exactly the two existing files and adds the regression file. The 17 other projected files remain exact.

The receiving driver invokes the actual `python -m testpilot compare` command eight ways in normal Python and again with an explicit `-O` child argument. It uses fictional retained reports, real local pipes and real output files.

| Case | Original status | Candidate status |
| --- | ---: | ---: |
| Open UTF-8 console | 0 | 0 |
| Open ASCII console, ordinary path | 0 | 0 |
| Closed stdout pipe after complete publication | 120 | 2 |
| Unicode output path on ASCII stdout | 1 | 2 |
| Both console pipes closed | 120 | 2 |
| Occupied output destination | 2 | 2 |
| Invalid input with closed stderr | 120 | 2 |
| Unicode input-error diagnostic on ordinary Python stderr | 2 | 2 |

Both execution modes produced the same statuses. Original receiving passes 8 of 16 cases; the candidate passes 16 of 16. All successful publications retain the same 12,638-byte HTML with SHA-256 `29ea4d914d511511f8d58aca7c7c4c00d27cafeb71b5d9d87f402bf31348aca8`. The input JSON bytes, occupied output and all source files remain unchanged.

The four relevant maintained comparison modules passed **57 tests**, with no skips:
`test_compare.py`, `test_compare_cli.py`, `test_compare_cleanup.py`, and `test_compare_console.py`.
That run and the frozen production course used predecessor test blob `6bab3aacb08670f957a494d682cecdf9785113c4`. Root review then identified two raw subprocess assertions that assumed LF output. Only those assertions changed to compare `splitlines()`, preserving the exact in-process StringIO newline checks. Production source and the frozen Linux course stayed unchanged.

The final seven console cases then passed **7/7 on native Windows 11 / CPython 3.14.3**, with no skips and all 20 projected source files unchanged. `final-windows-tests.json` records that separate final test-file qualification. These are the comparison subset and a bounded Windows regression-module run, not the entire TestPilot suite. No second whole-suite or production-course rerun is claimed.

## Retained evidence and one corrected receiving assumption

`baseline-original-receipt.json` and `receive_compare_console_v1.py` retain the exact first course. Its expectation that a Unicode diagnostic would be silent on ASCII stderr was wrong: Python's stderr backslash-escapes those characters. That ordinary input-error case correctly returned 2.

`baseline-reconciled-receipt.json` corrects only that expected diagnostic and records the original receipt identity. No native command was rerun to make that correction. `receive_compare_console.py` contains the corrected expectation used by the candidate course. The four observed product-failure cases above are unchanged by this correction.

Each receipt retains actual argv, optimization mode, exit status, output-file identity, exact stdout/stderr text and hashes, and before/after source hashes. A separate check verified that re-encoding every retained stream text reproduces its recorded byte hash. `source-review.json` records the exact three-file scope, final test identity, and that unchanged stream custody check. `maintained-tests.json` retains the actual comparison-test command and complete output.

`fixtures/before.json`, `fixtures/after.json`, and `fixtures/comparison.html` are the fictional input pair and actual complete candidate page. They support a portable manual replay.

## Replay

From a source checkout containing the candidate:

```sh
python -B docs/receiving/compare-console-dcac8b3b8755/receive_compare_console.py \
  --source . --out /existing/parent/new-console-receiving
python -B -m pytest -q tests/test_compare.py tests/test_compare_cli.py \
  tests/test_compare_cleanup.py tests/test_compare_console.py
```

The receiving destination must not exist. Use a suitable local temporary directory for pytest when the system temporary volume is full.

During the final test-only correction, the ThinkPad home volume filled and the attempted test-file write was truncated. The exact original publication packet and completed receipts were recovered read-only; only this contribution's reproducible pytest scratch was removed, and the final test file was restored from its retained source. The failed follow-up did not produce a test-pass receipt. The final seven-case run moved to the separate Windows workspace described above.

This qualification invokes no model, external provider, project pytest child, installed consumer or GitHub Actions workflow. Source publication and any later main adoption remain distinct from an installed-runtime change. Independent native receiving is recorded separately when available.
