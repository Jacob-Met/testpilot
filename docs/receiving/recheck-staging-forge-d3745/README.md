# Retryable saved-test recheck output staging

Source contribution: [issue #103](https://github.com/Jacob-Met/testpilot/issues/103).
Author-qualified native source, independently reviewed writer/test change, and accepted complementary native CLI receiving.

## Developer result

The three saved-test recheck reports are now fully written in temporary files on the destination filesystem before the writer exclusively creates its final directory. If ordinary report preparation or staging fails, the requested final path remains absent. The caller can correct the problem and explicitly repeat the command with that same output path.

The command still refuses an occupied destination. It does not retry automatically. Final moves are individual: a later publication error may leave a partial final directory, and a later command must select another absent path. New parent directories may remain after failure. There is no transaction, crash-durability or concurrent-writer guarantee.

Successful Markdown, JSON and HTML bytes, native newlines, permission modes, names and returned path mapping remain compatible. The HTML download retains exactly the sibling JSON bytes. The parser, renderer, pytest execution, generated-case collector, CLI exit meanings and model behavior are unchanged.

## Frozen source and review

Baseline commit: `ffc2590682f30c3ff23084aacb79a8f50111f273`  
Baseline tree: `06621982a9dd96ab7efe2587a5c2f7e5561733b6`  
Original recheck Git blob: `b5d0b705c30c03e6b7e7e90b83e8dc83b8f9de52`  
Original recheck SHA256: `3eab07bd639994f897f76c0cd2b941d5e294c6d7c8132c82deb800e44d7079e6`  
Candidate recheck SHA256: `1b7d31f49cede49c45fe1fb0613b6e55fac292a7dece9b2645d1b55b141d95f6`

The production change adds only the tempfile import and changes `write_recheck_outputs`. Root independently read the entire writer diff and all seven new maintained tests, then separately accepted the intentional update to the historical partial-file assertion. The exact source map is in `source-freeze.json`.

Generation output staging remains with its existing owner. Recheck admission, timeout, selection, rendering and other repository work remain unchanged. The current complete tree had no AGENTS.md or CODEOWNERS. The sole workflow was read and left unchanged; source publication carries skip markers and no workflow activation.

## Actual failure and recovery

The retained public-writer probe uses an explicitly authored serializer fixture; it does not claim a pytest or provider run. A child-only 4,096-byte POSIX file-size limit produces the real EFBIG error. Parent limits and other processes are unaffected.

| Course | Original writer | Staged writer |
| --- | --- | --- |
| Unrestricted writer | Complete MD/JSON/HTML | Complete MD/JSON/HTML |
| HTML write reaches the file-size limit | Complete earlier MD/JSON and a truncated 4,096-byte HTML remain in the final directory | Final directory absent; temporary stage removed |
| Caller explicitly repeats with the limit removed | Existing final directory is refused | Same destination succeeds with all three complete reports |

Original unrestricted artifacts were 714-byte Markdown, 1,696-byte JSON and 9,362-byte HTML. The candidate probe has one additional byte in its recorded project path, so its corresponding JSON/HTML sizes are 1,697/9,363. This path difference is not a serialization comparison. The maintained parity oracle uses the **same result** and independent original native file-writing operations; all three artifact bytes and modes match.

The focused tests exercise real file-size failures during each of MD, JSON and HTML staging, corrected explicit retry, literal Unicode/mixed newline parity, exact HTML JSON download, preparation and encoding failure, occupied destinations and late occupancy, stage cleanup, and the documented late-move partial-delivery limit.

## Native qualification

Cloud Python 3.12.14 ran all seven new unittest methods successfully both normally and with `-O`. Child commands inherit optimization for those tests. No pytest was installed in that cloud interpreter.

Native receiving used the existing ThinkPad `/usr/bin/python3` 3.14.4 and installed pytest. The device configuration, uid1000/user jacob, free space and absent exclusive stage were checked. All temporary projects and child TMPDIR were inside the new owned stage; no installation or existing developer checkout was used.

The first native receiver, PID2950091, retained:

- Original inherited recheck/HTML suite: **44 passed**.
- New focused controls on the original writer: seven methods ran with six recorded failures, including expected subtest failures.
- Candidate with the unchanged historical HTML assertion: **43 passed, one failed**. That test explicitly required a partial final JSON/HTML after an HTML write error.
- Candidate new controls: **seven passed normally and seven passed with -O**.
- All baseline and candidate source bytes remained unchanged during that course.

The historical assertion was then explicitly updated: the actual limited CLI returns output error2, writes no final directory, and leaves no temporary stage; a separate unlimited invocation using the exact same CLI input/output destination succeeds. Its complete reports, exact embedded JSON and preserved saved input/project are checked.

Final native receiver PID2985058 ran `tests/test_recheck.py`, `tests/test_recheck_html.py` and `tests/test_recheck_output_staging.py` together: **51 passed plus 12 subtests passed**, exit0, empty stderr, with all 18 source/config/test files unchanged before and after. The original 44-pass and 43-plus-one receipts remain immutable; they were not replaced by the final receipt.

## Independent preserved-boundary receiving

Anvil independently froze and ran a complementary actual-CLI course on both baseline and candidate: a genuine known-good neighboring recheck, duplicate-key saved-report refusal into a new sibling destination, then an explicit corrected-input repeat with the identical CLI arguments and destination. Both courses passed 29 checks and returned exit0 from their receivers. The successful repeat ran the retained pytest, wrote all three reports and delivered exact JSON through the HTML download. The known-good neighboring report, project, input controls and all 14 production modules/modes stayed unchanged.

This is a preserved admission/recovery control, not a new admission repair or another staging-failure witness. Its exact receiver, two receipts and narrative are in `independent/`. Native receiver PIDs were2986269 and2987262.

## Reproduce the bounded checks

From the source root with the project's pytest dependency already available:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -B -m pytest -q -p no:cacheprovider \
  tests/test_recheck.py tests/test_recheck_html.py tests/test_recheck_output_staging.py
```

The seven new controls also run without pytest:

```sh
PYTHONPATH=. python3 -B tests/test_recheck_output_staging.py
PYTHONPATH=. python3 -B -O tests/test_recheck_output_staging.py
```

Choose an owned writable TMPDIR when shared temporary storage is full. POSIX file-size controls skip on other platforms. No Windows run is claimed.

The native receiver sources and exact initial input packet are preserved for provenance. The initial receiver intentionally demonstrates the original HTML-test policy conflict; it is not the final passing test command. `receive_final.py` uses the corrected maintained test bytes, identified in the final source map. Use the normal commands above for current-source reproduction.

## Receiving files and limits

`author/` contains the exact original/candidate writer observations, original probe, cloud test receipt and source/test diffs. `native/` retains both executed receiver sources, the original incoming source packet, initial receipt and final receipt. These observations are bounded local writer and real saved-test CLI checks, not a full repository suite or live-provider qualification.

A shared-scratch ENOSPC interrupted the first attempt to save the new test file; the resulting empty file did not execute tests. The exact test source was restored from retained content and authenticated before execution. An attempted separate /dev path did not persist across tool processes. The successful cloud controls therefore materialized and executed an owned /dev copy within one process, then saved the exact source and receipts back to the shared stage. No peer files were deleted or changed.
