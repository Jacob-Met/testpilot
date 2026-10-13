# TestPilot saved-run finder — recovered issue39 public contract

Owner of this continuation: Loom / d3745; root independently receives the command. Original issue39 contract and estate-8ef1dfe65b8f/source_integration credit remain. This document precedes candidate implementation. Source basis: `f9ba2d2260f7aa93b3958661aa178ad418df9af6`, tree `6aec92096d7786defc448dc2e5adba838771bcfd`.

## Operator outcome and interface

Find retained generation and recheck reports under one explicit directory without running tests, models, project code or recorded paths. Results describe saved claims, not renewed verification or chronology.

`python -B -m testpilot history --root DIR [--max-depth N] [--status VALUE ...] [--query TEXT] [--kind generation|recheck] [--json]`

API: `scan_history(root, *, max_depth=1, statuses=(), query=None, kind=None) -> dict`. `HistoryError(ValueError)` represents invalid options/root. The API does not print. `root` accepts a string or Path; max_depth is an exact integer 0..8, excluding booleans. statuses is a list/tuple of strings, query is string/None, kind is generation/recheck/None. Literal empty strings and repeated status values are allowed. Option admission precedes any filesystem access. The CLI keeps ordinary argparse refusal precedence. Unknown status labels are valid literal filters.

Resolve the explicitly selected root once with strict existence. It must be a directory; an explicit root symlink may resolve to that directory. Report the resolved absolute root. Invalid root/options produce CLI exit2, no stdout, and `testpilot: cannot scan saved runs: MESSAGE` plus LF on usable stderr. No directory is created. Do not change cwd or environment.

## Discovery, ordering and finite work

The root's files have depth0; each entered subdirectory adds one. Default1 includes root and immediate child directories. max_depth0 reads only root files. Deeper directories are intentionally outside the selected scope and do not make the selected scan partial.

Enumerate each visited directory once, counting all directory entries, including ignored names and links. Sort an admitted directory's entries by exact Python string name and visit in depth-first order. Skip every internal symbolic link without following it or treating it as a candidate; this includes links named report.json/recheck.json. Directories with those names are ordinary directories, not report candidates. A non-directory, non-symlink entry named exactly report.json or recheck.json is a candidate; other names are ignored. Acquire only regular candidate files with bounded binary reads. No FIFO/device body is read. Directory/read/admission problems do not hide already accepted healthy siblings.

Budgets are fixed: 1,000 candidate files; 20,000 directory entries; 16MiB per report; 64MiB total bytes read from report bodies. These include rejected candidate bodies; filters do not reduce discovery or admission work. At a candidate limit, stop before opening the next candidate and add one `candidate_limit` problem at its relative path. At a total-byte limit, stop before reading a candidate whose recorded size exceeds the remaining budget and add one `total_bytes_limit` problem there. Exact-boundary files can be admitted. A per-report oversized file is a `report_bytes_limit` problem and healthy later siblings are still considered.

A directory enumeration may observe one additional entry solely as an overflow witness. If it exceeds the remaining entry allowance, discard that directory's collected list without processing any of its children, set entries_seen to the20,000 limit, add `entry_limit` at that directory (root is `.`), and stop scanning. This avoids selecting a platform-dependent prefix from an oversized directory. The sentinel is not a report-body read. A directory enumeration error discards that directory's list, emits `directory_error`, and continues other admitted siblings. entries_seen includes entries actually observed before that error.

Body reads never exceed the remaining global allowance. Compare regular-file descriptor size before/after bounded reading; size change or incomplete capture is `read_error`, not an admitted snapshot. This is finite cooperative reading, not a hostile-path or concurrent-writer snapshot guarantee. A changed directory/file type is a directory/read problem. Stored path strings inside JSON are never opened.

After scanning, sort runs by relative POSIX-style path and problems by `(path, code)`. Directory traversal selects any budget-limited subset; the final ordering is by path, never timestamps. Hard-linked regular reports at distinct paths remain distinct rows. Relative labels preserve ordinary Unicode, spaces and literal controls as JSON escapes when printed.

## Structural admission

Decode captured bounded bytes as UTF-8 JSON, allowing a UTF-8 BOM. Reject duplicate keys, NaN/Infinity constants, nonfinite decoded floats, invalid Unicode/JSON, native parser recursion/integer limits, non-object roots and unsupported schema tags. Such a file is one problem row and makes the scan partial. Additional fields are allowed; nothing is rewritten. This is structural core admission, not full semantic consistency, origin authentication or a replay of recorded execution.

Generation records have absent/null schema and all native LoopResult core fields: status, changed_functions, repair_rounds_used, max_repair_rounds, test_files, tests_written, final, patch, coverage, ledger, rounds, plan, message. Status is one of passed/failed/suspected_code_bug/no_changes/no_tests/budget_exhausted/model_error. Counts are nonnegative exact integers (not bool); plan/message/patch and test-file values are strings; ledger is an object, rounds is an array, coverage is null/object. Optional ok is an exact bool. Each changed function has string path/qualname/source, positive integer lineno/end_lineno with end>=start, and an array of positive integer changed_lines. Extra target fields remain outside the displayed summary. Empty targets/tests are legitimate generation evidence.

Recheck records have schema `testpilot.recheck/1`, status passed/failed/no_tests, exact-bool ok, string repo/python/started_at/finished_at, source_report object with string path/sha256 and string/null recorded_status, nonempty string-valued test_files, retained_tests array, final object, exact-integer model_calls, and string scope. Each retained_tests entry has string path/sha256/placement and nonnegative integer bytes. Do not parse timestamp labels, infer ordering or equate the saved source_report hash with any file now on disk.

For either kind, final may be null only for generation. Otherwise require the native core: integer returncode; bool timed_out/ok; finite nonnegative duration_s; string output/summary; nonnegative integer passed/failed/errors/skipped; cases array; null/object coverage. Optional junit_available must be bool. Optional timeout_s is null or finite nonnegative number; optional generated_files is an array of strings; optional generated is null or an object. Case/detail/ledger content is not displayed or independently reconciled. Missing historical junit_available is represented as null, not false or a fabricated zero-execution conclusion.

The filename discovers a record; its admitted schema determines its kind. A generation-shaped recheck.json is therefore a generation row, rather than a guessed recheck. Unknown non-null schema produces `unsupported_schema`; malformed native core produces `invalid_report`; UTF-8/JSON/duplicate/nonfinite/parser failures produce `invalid_json`.

## Filters and public JSON

Repeated statuses use exact-string OR. Separate filters use AND. Query is a casefolded literal substring of the relative report path, each target path and qualname, or each retained test path. It does not search source bodies, diagnostic output, recorded source_report paths or status. Empty query matches every admitted row. All reports are admitted before filtering; an invalid unselected neighbor still makes complete=false.

JSON output is `json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2) + '\n'` (UTF-8). The complete object has exactly these keys:

```json
{
  "schema": "testpilot.history/1",
  "root": "RESOLVED_ABSOLUTE_ROOT",
  "max_depth": 1,
  "filters": {"statuses": [], "query": null, "kind": null},
  "complete": true,
  "limits": {"candidate_files": 1000, "directory_entries": 20000, "report_bytes": 16777216, "total_bytes": 67108864},
  "counts": {"entries_seen": 0, "candidate_files": 0, "bytes_read": 0, "admitted": 0, "matched": 0, "problems": 0},
  "runs": [],
  "problems": [],
  "notice": "Saved records only. Reported outcomes are historical; no tests or model calls were run. Results are complete only within the selected root, depth and stated budgets; paths are not chronology."
}
```

filters.statuses preserves the supplied order/repetitions. admitted counts all structurally accepted records before filters; matched equals len(runs). candidate_files counts candidates actually considered (including per-file/type/admission problems), excluding the overflow candidate that terminates scanning. bytes_read counts all acquired report-body bytes, including rejected bodies, and never exceeds total_bytes. complete is exactly `not problems`.

Each run has exactly `path`, `kind`, `bytes`, `sha256`, `status`, `targets`, `test_paths`, `final`, `recheck_context`. targets preserves source order and duplicate labels as objects with only path/qualname; it is empty for recheck. test_paths is sorted exact strings. Raw byte length/hash describe the captured report, including BOM/newlines. final is null or an object with exactly summary/returncode/timed_out/passed/failed/errors/skipped/junit_available. Every value is literal saved evidence; absent junit_available becomes null. recheck_context is null for generation or an object with exactly repo/python/started_at/finished_at/source_report; source_report has exactly path/sha256/recorded_status from the record.

Each problem has exactly path/code/message. Fixed messages: `candidate_limit`: "Candidate-file budget reached."; `entry_limit`: "Directory-entry budget reached."; `total_bytes_limit`: "Total report-byte budget reached."; `report_bytes_limit`: "Report exceeds the per-file byte limit."; `directory_error`: "Could not enumerate this directory."; `read_error`: "Could not read a complete regular report."; `unsupported_schema`: "Unsupported saved-report schema."; `invalid_json`: "Not supported finite UTF-8 JSON."; `invalid_report`: "Not a supported generation or recheck core record." Problem messages do not expose source bodies or unstable OS exception prose.

## Text output and exits

Default text is ASCII-safe and line-oriented. Use compact sorted-key ensure_ascii JSON (`json.dumps(value, ensure_ascii=True, sort_keys=True)`) for every value below. Header lines, in order:

```text
TestPilot saved-run history
Root: JSON(root)
Complete within selected scope: true|false
Counts: JSON(counts)
Filters: JSON(filters)
```

For each matching row: `Run: JSON(path) | KIND | JSON(status) | BYTES bytes | SHA256 HASH`, then two-space-indented `Targets: JSON(targets)`, `Retained test paths: JSON(test_paths)`, `Recorded final: JSON(final)`, and `Recheck context: JSON(recheck_context)`. Each problem is `Problem: JSON(path) [CODE] MESSAGE`. End with the exact notice line and one final LF. No source or retained-test contents are printed.

Exit0 means a complete selected scan, including zero matches. Exit1 means partial results with at least one problem; print the complete available result before returning1. Exit2 means invalid options/root or stdout delivery failure. Write and flush the selected complete rendering once; failed output may be partial and is not retried or redirected. Absent/failing stdout returns2; a usable stderr may receive `testpilot: cannot write saved-run history`. Retain no project/report/output mutation. Interpretation of a historical status never permits retry, test adoption or patch application.

## Source fence and original evidence

New history.py, tests/test_history.py and docs/HISTORY.md; only additive history CLI import/parser/dispatch and one README usage section. All existing command spans stay exact. New evidence uses docs/qualification/saved-run-finder-loom-d3745/. No dependency, active workflow, installed executable, renderer, provider, sandbox, selector or saved-report mutation.

The current original source projection is authenticated in source-intake-v1.json. Its two eval reports remain producer-retained fixtures; any additional recheck fixture is openly authored. A small original `history` refusal precedes implementation. Root owns distinct independently authored corpus/oracles; candidate source remains withheld until that receiver freezes.
