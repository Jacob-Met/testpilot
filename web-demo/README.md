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
