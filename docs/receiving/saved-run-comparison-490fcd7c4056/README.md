# Saved-run comparison: native receiving record

Issue: https://github.com/Jacob-Met/testpilot/issues/26

This contribution adds a consumer-only compare command and an offline review page for two saved native TestPilot reports. The source is frozen for independent receiving; publication and current-main composition are owned by the parent integration worker.

## Exact source

Base commit: e1d87442eeecc8cf1b44ee3547849d5c1d030876  
Base tree: 1466e2d4a2a1f2ce4fe5293e55e0b7f7e0b3797a  
31-file candidate manifest SHA256: c6b4074dc7361ce896f32f9f36008ace1b7aebde0f359991ae36b85189c815b4

Seven contribution paths: README.md, docs/COMPARE.md, testpilot/__main__.py, testpilot/compare.py, testpilot/compare_html.py, tests/test_compare.py, tests/test_compare_cli.py. The new receipt directory contains evidence only.

All 26 materialized baseline source/fixture files match fetched Git blobs and retained SHA256 identities. All 24 inherited candidate files outside README and CLI remain byte-identical. Removing exactly the added compare parser and early dispatch reproduces the base CLI bytes. The complete 1,162-entry tree is retained; other tree leaves are references, not a claim that every historical artifact was copied or tested. No AGENTS.md or CODEX_HANDOFF.md exists in that pinned tree.

This change does not alter generation, raw-diff loading, target selection, model/provider code, pricing, sandbox execution, collector behavior, or the existing single-run HTML renderer. Shared CLI integration must preserve the separate #25 raw-diff and saved-test-recheck branches.

## Actual baseline and author qualification

The native Linux host used Python 3.14.4, pytest 9.0.2, coverage 7.16.2, Node 22.22.1, and Chromium 154.0.8037.57. Existing tooling was reused read-only.

Two real TestPilot CLI runs used the maintained calc_clamp fixture, its maintained scripted replies, and one repair round. The Before project retained the buggy implementation; the After project used the maintained fixed implementation. Both source projects and all baseline files were preserved.

| Check | Result |
|---|---|
| Before actual run | Exit 1, suspected_code_bug; 3 generated failures and 1 generated pass |
| After actual run | Exit 0, passed; 6 suite passes, including 4 generated cases |
| Unmodified baseline compare command | Exit 2; argparse reports no compare command and no HTML is created |
| First candidate comparison of the exact two reports | Exit 0; complete offline page written |
| New focused tests, first run | 38 passed |
| Inherited CLI targets, interpreter, and single-run HTML tests | 36 passed plus 6 subtests |
| New focused tests after the phone-layout repair | 38 passed |
| Browser qualification, final | 4 groups passed; 4 actual JSON downloads matched the input bytes exactly; no external requests or page errors |

Actual baseline report identities:

- Before: 12,461 bytes; SHA256 01291ef8dbcf71d343905584538337d56ad2d8872a2692f9293e8f043a58dc55.
- After: 8,085 bytes; SHA256 bebc3a29d269c0988711d3a8d934faa520d2e3f243a923d2ab9530c749a8212d.

The browser ran with page JavaScript disabled. It exercised actual statuses and suite/generated distinctions, native Tab/Enter/Space navigation, expandable source panels, focus visibility, role-specific downloads, literal markup/separators/surrogates, added empty source files, unavailable JUnit/coverage, incomplete cost, and a 390-pixel viewport. The literal pair is explicitly a changed-input fixture, not a claim that another test run occurred.

## Observed defect and narrow repair

The first browser run passed its first three groups and all four exact-download checks, then failed the 390-pixel layout assertion: document width was 846 pixels. Long source panels exposed the implicit content minimum of the mobile one-column grid.

The renderer now gives grid children a zero minimum width and uses minmax(0, 1fr) for the mobile track. The browser driver changed only its output artifact/screenshot paths; its assertions stayed the same. The rerun passed all four groups with document width 390 pixels. The original failed receipt, pre-fix renderer, HTML, driver, diagnostic measurements, and screenshot are retained in the native archive. The successful desktop and phone screenshots were visually inspected.

## Semantics and practical limits

Recorded status and metrics are presented as producer claims. Before/After labels do not prove chronology; equal selected source does not establish equal repositories, test selection, or execution environments. Duplicate labels are separate records. Different file paths remain additions/removals. The view does not recompute outcome, pass-rate improvement, cross-run coverage, or pricing.

Unknown execution evidence and missing coverage remain unavailable; incomplete price remains unpriced. JSON is decoded with bounded, strict admission and Decimal precision. Exact original bytes remain in static download anchors. Output publication refuses any existing destination, including input aliases, and completes admission/rendering before staging output.

This packet qualifies Linux/Chromium behavior at the pinned source. It is not a Windows/Safari/Firefox, provider, or current-main integration claim. The parent independent receiver uses different actual source projects and reports, and its results should be appended with their own exact pins rather than folded into these author totals.

The native archive retains complete candidate/baseline materialized source, original report artifacts, modified fixtures, all drivers, logs, manifests, screenshots, and receipts. No real user repositories, accounts, or credentials were used.
