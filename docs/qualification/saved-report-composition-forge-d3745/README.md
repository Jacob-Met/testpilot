# Saved report reopening — current-source composition

This integrates the existing issue #88 contribution from owner 9730e9219220 / portfolio without changing its three source, test or guide files. The contribution lets a caller explicitly select an archived generation report and its matching patch, then create a new passive HTML review with the exact input bytes embedded for download.

## Open a saved pair

From a checkout containing the contribution, using Python 3.12 or newer:

```sh
python -m testpilot.saved_report --report eval/results/calc_clamp/report.json --patch eval/results/calc_clamp/testpilot.patch --out calc-clamp-review.html
```

Open the resulting HTML directly. The saved result remains historical: this command does not execute retained tests, call a model, apply the patch or recompute the result. Exit 0 means that the review was created, including when the recorded status is suspected_code_bug. The module has its own CLI; it is not a newly added main testpilot subcommand. The maintained [saved report guide](../../SAVED_REPORT_REVIEW.md) describes the input limits, exact newline forms, destination ownership and console-error boundary.

Select both inputs explicitly. If the pair is refused and the destination remains absent, correct the cause and invoke the command again. An existing output is preserved and refused; choose a fresh name. A console failure after publication can leave a complete page, so inspect the output before deciding how to retry.

## Exact source composition

- Current first parent: 247ad1ae8e873fcd52935633015158a1060091af, tree 90e4dc3e36a8575cbad2778dc4d6b7fd109b2e64.
- Existing contribution: 17643838400fa85149e474622e677008cdcc3f79.
- Added files only: testpilot/saved_report.py, tests/test_saved_report.py, docs/SAVED_REPORT_REVIEW.md.
- The current native renderer remains blob 3281bd01b5df5c3122bf95fe4f3bdbc2217642ee. All other current source, README and workflow files remain inherited.
- [source-binding.json](source-binding.json) gives each exact source identity; [source-admission.json](source-admission.json) records the 49 received native files.

This is source-aware composition qualification, performed after reading the existing contribution. Original ownership, source history and earlier qualification remain separate. The existing contribution is preserved as a second commit parent rather than copied into an unrelated author history.

## Actual native receiving

The author-owned receiver ran on the ThinkPad with Python 3.14.4. PID 3860172 exited 0. Five actual commands and 32 recorded comparisons passed:

| Course | Exit | Observed result |
| --- | --- | --- |
| Current source before the addition | 1 | Module absent; no output created. |
| Exact donor maintained test file on composed source | 0 | All 8 methods passed. |
| calc_clamp report with the selected stats_median patch | 2 | Pair refused; inputs preserved; no output or staging file. |
| Explicitly replace only the owned selected patch with calc_clamp's exact patch; repeat identical argv and destination | 0 | A 39385-byte passive page was created with exact report and patch downloads. |
| Repeat against the occupied output | 2 | Complete prior page and both selected inputs remained byte-identical. |

The successful page SHA256 is b70d5a30d79b56fab426ed230ff47be2b375b6f448cf8482dd0e37ea0905f674. The original report is 11467 bytes, SHA256 00ce7170150b268cf7484de03658cb4af8f61bcdd64f1500dee46dfe004d52ac; its patch is 561 bytes, SHA256 271ea1507ff20439503261e59984ce8d8e04cbf72a6d85c0e2dca7a05b9bf4bc. Historical status stayed suspected_code_bug.

The preserved donor test includes three actual optimized child archive courses. The suite parent and new receiving CLI commands used Python -B -S; the donor subprocess arguments are unchanged. This is not a claim that every nested process used -S or that all 8 methods ran in an optimized parent.

[composition-receipt.json](composition-receipt.json) retains all 32 comparisons, full command arguments and child PIDs, complete captured output, and before/after identities. Its ten raw streams are separately retained under [streams/](streams/). All 49 source files and 5 receiving controls retained exact bytes and native modes. The receipt itself is 47385 bytes, SHA256 567769f42c4fcf43550e7f502fcf0253a71d204341c6783716e802f13948cc96.

Anvil independently read the complete receiver, criteria and receipt, matched all 10 streams, bound the 49 native source files to both complete Git trees, checked the exact saved page/downloads and confirmed all 6 recorded PIDs were gone. [retrospective-review.json](retrospective-review.json) records that completed read-only audit. Its original native review remains pinned there, with body retrieval pending after a device connection outage. No product replay or browser receiving occurred. [root-source-review.json](root-source-review.json) separately records the accepted production/source design review.

## Retained inputs and scope

The exact executed staging source, receiving source, criteria and input packet are retained. The packet contains the 23 current selected files and 3 donor files. The stage script creates an original 23-file projection and a composed 26-file projection exclusively; this is not a full checkout. Its original paths and modes are preserved in the receipts. To reproduce, use a fresh exclusive stage with the same files and prerequisites; the archived receiver's existing consumer/evidence outputs must not be reused as an empty stage.

The actual corrected pair and resulting page remain in the original native consumer directory. The input packet includes the original archived report and patch bytes. The page's recorded digest and all command streams are preserved here; its full body was not exported before the device connection outage. Git records regular-file mode 100644; receipts retain actual native permission values, including the generated page's 0600 mode. [custody-recovery.json](custody-recovery.json) identifies the exact retained bodies recovered from prior tool output, each matched to its original native SHA256.

No provider, model request, saved generated-test execution, full-suite qualification, browser rendering, Windows runtime or installer behavior was exercised in this composition course. The maintained test launches its own controlled tests of the saved-report module; it does not execute the archived generated tests. Existing adjacent source owners and their evidence remain untouched.

## Worked page delivery after the outage

A separately rendered cloud copy now provides the exact 39,385-byte page matching the native receipt's full SHA-256. The original receiving and outage records above are retained unchanged. [Open the worked result and read its reconstruction provenance](delivery/README.md); the delivery page, exact reconstruction command/streams and independent review are linked there. Source adoption is merge `6f0aa5d9c4394d0f104a7b8b164c5765c2529f9c` through [PR 119](https://github.com/Jacob-Met/testpilot/pull/119).
