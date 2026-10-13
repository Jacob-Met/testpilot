# TestPilot regression replay

A static browser product backed by actual recorded TestPilot and pytest runs.
Choose a fixture, inspect the diff and authored test plan, read the generated
test result, and compare the exact tests against the fixture's ground-truth fix.

The two examples deliberately show different outcomes:

- **Clamp boundaries:** the generated tests expose the changed implementation;
  TestPilot retains the failures as a suspected code bug. The same assertions
  pass with the ground-truth fix.
- **Even-length median:** the generated tests pass while the bug remains. A
  separate authored boundary witness fails before the oracle fix and passes
  after it. The generated patch is kept distinct from that independent witness.

These are authored `ScriptedModel` replies and recorded local Python execution.
The browser does not execute Python, call a model, or generate fresh test output.
Replay navigation only reveals the bundled recording. These toy examples do
not measure model quality.

## Open the demo

From this directory, use any static server. Python's standard library is enough:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Open <http://127.0.0.1:8000>. Opening `index.html` directly as a `file:` URL will
not reliably allow its JSON fetch; the page reports a loading error instead of
inventing a result. All runtime assets are local. No package installation,
remote font, API key or external service is needed to replay the recording.

The stage tabs support Left/Right, Home and End keys. Fixture and stage query
parameters are shareable, for example `?case=stats_median&stage=4`. Download links
serve the exact generated patch, case JSON and complete generated-test log.

## Recording provenance

`source-pin.json` identifies the original TestPilot commit and the 27 source,
fixture and documentation blobs used in this bounded capture. The full source
repository remains authoritative; this demo changes no core TestPilot file.
`data/replays.json` records the actual runtime, capture time, capture-script
hash, test counts and exact artifact hashes. Full stdout lives beside each case.
Visible console panels use the source sandbox's output excerpt; the download
contains the complete captured stdout.

The oracle comes from the existing `eval/cases/*/fix` files and is applied only
inside a separate sandbox verification. It is never supplied to ScriptedModel.
Existing fixture files are checked before and after capture and remain unchanged.

To reproduce the recording, use Python 3.12+ with the project's declared pytest
dependency. Point `--source-root` at an exact checkout of the commit in
`source-pin.json`, and choose a new output directory:

```sh
python3 web-demo/tools/capture_replay.py \
  --source-root /path/to/pinned-testpilot-checkout \
  --output /path/to/new-recording
```

The capture script reads its pin beside itself, so it can run against a separate
checkout even if that older source does not contain `web-demo`. It refuses source
drift before importing the pipeline or creating output. It constructs
`ScriptedModel` directly; environment-selected provider clients and prices are
unused. Existing recordings are never overwritten. Execution durations and
temporary paths can vary; fixture outcomes and generated patch bytes must agree.

## Browser acceptance

`tools/check_browser.mjs` runs actual desktop and phone Chromium contexts, checks
fixture/stage and keyboard behavior, deep links, failure on invalid evidence,
overflow, and exact downloaded bytes. It uses an installed Playwright package
and browser, optionally selected with `TESTPILOT_PLAYWRIGHT_MODULE` and
`TESTPILOT_BROWSER_EXECUTABLE`. It creates no user profile and closes its browser
and ephemeral loopback server in `finally`.

```sh
node web-demo/tools/check_browser.mjs web-demo /path/to/new-browser-receipt
```

Native capture and receiving receipts are under `receipts/`. They identify their
own source and execution scope; they do not claim full TestPilot CI, live model
acceptance or service deployment.

## Disposable installation and rollback proof

The static receiver harness copies only the runtime assets and their data into
a new target, reads every byte over an ephemeral loopback HTTP server, moves the
owned target aside, checks that HTTP now returns 404, then reinstalls the same
bytes and reads them back again. Existing paths are refused; nothing is deleted.
The final installation and its rollback copy remain. The temporary server stops.

```sh
python3 web-demo/tools/receive_static.py \
  web-demo /path/to/new-static-receiver /path/to/new-receiving-receipt
python3 -m http.server 8000 --bind 127.0.0.1 \
  --directory /path/to/new-static-receiver
```

## License

Apache-2.0, matching TestPilot. The fixture source and authored replies are reused
from the pinned repository; ownership and the root license/notice are preserved.

## Recorded-run consistency

The replay checks each of its five required runs before exposing a fixture.
Counts must be nonnegative safe integers and agree with the retained case
outcomes. Each run must explicitly report no errors, skips or timeout. A passing
run requires process exit 0, at least one recorded pass and no recorded failure;
a failing witness requires exit 1 and at least one recorded failure. Missing or
contradictory evidence shows the existing loading error and leaves downloads
unavailable.

These checks establish consistency within the supplied recording. They do not
authenticate its origin, verify artifact hashes in the browser or execute tests.

The dependency-free application regression course runs with Node's test runner:

```sh
node --test web-demo/tests/run-evidence.test.mjs
```

It executes the exact application with a small DOM and a local fixture response,
checks all eight fixture/stage views and rejects malformed run evidence in every
required position before any verdict or download appears. Use the separate
browser acceptance command above to qualify real browser behavior.

### Native source qualification

The exact application and unchanged bundled data were received on Node
v22.22.1 on 2026-10-12. The same four maintained tests produced two passes and
two expected failures on original commit
`478f68adf01658a94a3ede22526da00f580785bd`, then four passes on candidate
`1c01e0b9b720f22b2c1a9ea5bfe08c6b66c35a55`. The passing course includes all
160 malformed-run controls and eight healthy fixture/stage views. Every
received source/data file remained byte-identical after execution.

The [native receipt](../docs/receiving/replay-run-consistency-719c8e1b4e10/receipt.json)
retains source identities, commands, complete test output and timing. This is
Node application qualification with an authored DOM. The browser receipts below
qualify the same application blob separately.

### Native browser qualification

The repaired application is Git blob
`3a1b379e62df5d4c14c76479dc81db6d0e66f0e1`. Its bundled runtime files
remain exact across these receiving courses:

| Course | Source and environment | Received behavior |
| --- | --- | --- |
| [Focused author browser course](../docs/receiving/replay-run-consistency-719c8e1b4e10/README.md#focused-native-browser-result) | Candidate `bfb5cc28`; Node 22.22.1 / Chromium 153 on Linux, 2026-10-13 | 21 checks: original contradiction witness, 16 healthy desktop/narrow views and four malformed-record refusals |
| [Independent browser course](../docs/receiving/replay-run-consistency-719c8e1b4e10/independent-browser-ccd6f8d65954/README.md) | Candidate `bfb5cc28`; Node 26.11.0 / Chrome 154 on macOS, 2026-10-12 | 69 checks: native pointer/keyboard navigation, deep links, malformed-record refusal and recovery; 12 actual browser downloads matched the recorded filenames, byte counts and SHA-256 |

The independent receipt binds all 28 runtime inputs to their Git blob identities.
It uses native DevTools input, and its 390px viewport is a desktop browser
configuration. Both courses retain their original source pins, raw results,
receivers and captures. The [illustrated review](https://docs.google.com/document/d/1TtzuRd92ZZ2kB6BEyo93qX3DrjyuiC9q5gnonKNlUA0/edit)
shows the independently received interface.

The [consolidation record](../docs/receiving/replay-run-consistency-719c8e1b4e10/consolidation.json)
preserves the independent evidence and the unrelated comparison cleanup from
main without changing any replay runtime file or maintained regression test.
These receipts cover recorded replay behavior. Independent source review,
the full Python suite, physical devices, and deployed-site adoption remain
separate qualifications.
