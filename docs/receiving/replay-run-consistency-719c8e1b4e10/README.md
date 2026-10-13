# Recorded-run consistency receiving

This directory retains the Node, focused author browser, and independent browser qualification for the TestPilot recorded-run consistency repair.

## Source repair

The original application at `478f68adf01658a94a3ede22526da00f580785bd` admitted contradictory success flags, process exits, counts and retained case outcomes. The repaired application validates every required run before rendering a verdict or enabling artifact links.

The application blob `3a1b379e62df5d4c14c76479dc81db6d0e66f0e1` was received from branch head `bfb5cc2830fbe535d705ac2649503e3ae7647224`. Its source is unchanged by this browser-evidence update. The existing [Node receipt](receipt.json) remains exact: original 2 passes / 2 distinguishing failures, candidate 4 passes, including 160 malformed controls and eight healthy views.

## Focused native-browser result

**Passed: 21 checks on 2026-10-13, Node v22.22.1, Chromium Chrome/153.0.8010.47.**

- The actual original browser app rendered a contradictory successful run and enabled artifact links.
- The repaired app rendered both bundled fixtures at all four stages, at desktop and phone viewport settings: **16 healthy views**. Selected case/stage, relevant generated output or witness, exact artifact links, and viewport fit were checked.
- Four malformed recordings were refused before any verdict or artifact link was enabled: contradictory process exit, missing cases, inconsistent failing-case count, and absent timeout completion result.
- Each result was tied to its exact fully loaded document URL. The loopback receiver recorded all **21 corresponding dataset responses**. Healthy responses preserve the bundled JSON values; negative responses change only the stated run field in memory.
- Page error and external page request lists were empty. All five received source placements remained byte-identical. The browser closed, its profile was removed, its loopback server stopped, and a subsequent process check found no matching owned browser process.

The final [browser receipt](browser-receipt.json) is the unchanged native output, SHA-256 `25657369eb1dd5aece48a2db9f6fae558e3f9dd5432dfb38971b4b0810d22256`. [Receiving history](browser-history.json) retains the native command, source/image digests and earlier receiver iterations. The first iteration's aria-attribute expectation error is explicitly distinguished from a product failure.

## Rendered evidence

The final screenshots were inspected. The existing desktop and phone layouts remain legible without observed overlap or horizontal clipping.

[Desktop screenshot](desktop.png) · [Phone screenshot](phone.png)

| Screenshot | Actual dimensions | SHA-256 |
| --- | --- | --- |
| Desktop | 1425 × 1266 | `d806e06d916cef2dedb9d43f21f5f38e48780d5571fd58d7b8998910493f52f4` |
| Phone | 390 × 1973 | `058d6de1eab9b83dd9c553d39f440dd736f5e87d57dc63cf5e0694f6b497c514` |

## Reproduce the focused course

The [receiver](check-browser.mjs) uses only Node built-ins and an explicitly selected existing Chrome/Chromium executable. It creates synthetic negative responses and a new owned browser/output directory. It changes no source files.

From the repository root, retain the original application separately, then invoke:

```sh
git show 478f68adf01658a94a3ede22526da00f580785bd:web-demo/app.mjs > /tmp/testpilot-original-app.mjs
node docs/receiving/replay-run-consistency-719c8e1b4e10/check-browser.mjs --browser /path/to/chrome --root web-demo --original-app /tmp/testpilot-original-app.mjs --output /new/browser-receipt-directory
```

The output directory must be new. This focused course qualifies native rendering and evidence refusal. Its own receipt does not include physical downloads or the full keyboard journey.

## Independent browser receiving

The separate delivery worker `ccd6f8d65954` received the exact repaired runtime at `bfb5cc2830fbe535d705ac2649503e3ae7647224` on macOS with Node 26.11.0 and Chrome 154 on 2026-10-12. The unchanged [independent receiving directory](independent-browser-ccd6f8d65954/README.md) includes its frozen contract, source payload, as-run receiver, full receipt, native publication inventory, browser logs and two captures.

That course passed **69 checks** and completed **12 actual browser downloads**. It covered both fixtures and every stage at desktop and 390px, native pointer and keyboard navigation, deep links, malformed-record refusal and healthy-data recovery. Each downloaded patch, case record and full log matched its filename, byte count and SHA-256. All 28 runtime source identities match this branch; the raw independent receipt remains SHA-256 `bece35948294667529b1f6f1283ded3edab9b5b4a16a982c2294eeeaa488e619`.

[Open the illustrated independent review](https://docs.google.com/document/d/1TtzuRd92ZZ2kB6BEyo93qX3DrjyuiC9q5gnonKNlUA0/edit).

## Consolidated source and evidence

The [consolidation record](consolidation.json) describes the exact tree union:

- Owner candidate `9c361b954f606ae8d1b2fe9109cdaf403935f340`, retaining the repaired application, maintained tests, Node receipt and focused browser evidence.
- Independent receiving commit `8c9246c84b02631110fed748b837da579e87e91a`, retained as a second merge parent with all ten added evidence files unchanged.
- Main commit `b751e1cff2b7902bbebd6e7040f764d49bcb1a46`, retained as a third merge parent with its eight disjoint comparison-cleanup changes unchanged.

Only the two guides and the new consolidation record are authored in this follow-up. All 28 replay runtime files, the maintained run-evidence test, all prior raw receipts and all received captures remain exact. No browser or Python suite was rerun for this documentation and evidence union.

The original receipt dates and source pins describe the executions actually performed. Independent browser receiving is available; independent source review, the full Python suite, physical-device qualification, main integration and site adoption remain separate.
