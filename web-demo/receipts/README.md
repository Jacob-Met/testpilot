# Native replay receiving — estate-81ba1ed0179c

Recorded 2026-10-08 from TestPilot source
`ca2e6c72743c5d3866f3f14189f1d4c3405f60bf`. This is a new static product under
`web-demo/`; no core pipeline, model, sandbox, README or CI source was changed.

## Actual fixture capture

GL63's existing HamonWorker WSL ran the exact pinned source with Python 3.12.3
and pytest 8.4.2. The source manifest contains 27 exact Git blobs. The runtime
used `ScriptedModel` and the existing authored fixture replies; no live model
client was instantiated. Coverage was deliberately disabled for this capture.

| Case | Existing suite | Generated tests, buggy code | Same tests, oracle fix | Independent witness, buggy → fixed |
| --- | --- | --- | --- | --- |
| Clamp | 2 passed | 3 passed, 3 failed, exit 1 | 6 passed, exit 0 | 2 passed / 1 failed → 3 passed |
| Median | 1 passed | 4 passed, exit 0 | 4 passed, exit 0 | 1 passed / 1 failed → 2 passed |

No run timed out or reported errors/skips. Clamp retains the generated failing
assertions under `suspected_code_bug`; median's green generated tests miss the
even-length boundary. The independent witness is not part of the generated
patch, and the oracle is not input to ScriptedModel.

A second actual capture reproduced the outcome sets and both patch hashes.
Changing one source file in a disposable copy was refused before import or
output creation. Original pinned files remained byte-identical. The native
wrapper then hit a metadata-only `Path`/subprocess variable-shadowing error;
an export-only continuation checked the completed logs, source bytes, outcomes
and patch hashes. It did not relaunch unknown work or invent a run result.
The raw capture, recapture and refusal logs, and this continuation, are retained
in the `native-*` files.

## Actual browser behavior

Native Mac Google Chrome **154.0.8037.98**, Node **26.3.0**, existing Playwright
**1.62**, with fresh headless contexts and no user profile:

- Final **77 checks passed** at desktop 1440×1000 and phone 390×844.
- All four stages for both fixtures, honest caught/missed outcomes, oracle and
  witness panels, previous/next navigation, deep links and fallback, keyboard
  stage controls, and the keyboard skip link were exercised.
- **12 actual downloads** matched the recorded SHA-256 and byte length: patch,
  case record and full generated stdout for both cases on both viewports.
- No external browser request, page error, or document-width overflow occurred.
- Corrupted execution metadata produced the loading error and hid the replay.

The first automated pass had 71 checks; its full-page phone screenshot revealed
an offscreen skip link appearing inside the capture. The CSS now hides it until
focus, and the final six additional keyboard checks prove it remains usable.
The final screenshots were visually inspected. Browser processes and the
ephemeral loopback server were closed after each run.

`browser/receipt.json` retains the actual browser assertions and download hashes.
`browser/source-sha256.json` independently reads back all 40 transferred product
and capture files. `browser/desktop.png` and `browser/phone.png` are actual final
native renders, not generated mockups.

## Actual installed receiving and patch consumption

GL63 WSL received the frozen static product at
`/var/tmp/testpilot-replay-81ba1ed0179c/installed`.

- **32 static assets**, including all recorded artifacts and license notices,
  were read byte-for-byte over HTTP after installation.
- Rollback moved only that new directory to `installed.rolled-back`; requesting
  `index.html` returned **HTTP 404**.
- Reinstalling the same bytes passed all 32 HTTP checks again: **64 successful
  byte/hash readbacks** in total. The final directory and rollback copy remain;
  the ephemeral server stopped.
- Both actual downloadable patches passed `git apply --check` and `git apply`
  in separate disposable fixture copies. Pytest reproduced the recorded buggy
  result, then passed after copying the oracle. Existing fixture test files
  remained byte-identical. These are real Git and pytest child processes.

The 11 receiving subprocesses and raw outputs are in `installed/`. Expected
nonzero regression results are recorded separately from successful receiving.
This does not claim full repository CI, hosted deployment or live model quality.

## Ownership and source custody

The native `build-demo-testpilot-replay` goal had been explicitly reconciled as
failed read-only discovery with no project write or task submission. This
external contribution does not change its task state or claim a native lease.
The exact public source claim is TestPilot issue #7. Existing loop, sandbox,
diff/CLI and CI ownership remains with its contributors.

Native source, initial/final capture, changed-source control and installed
receiver remain under `/var/tmp/testpilot-replay-81ba1ed0179c` on GL63 WSL.
Native browser source and raw runs remain under
`/tmp/testpilot-replay-81ba1ed0179c` on the Mac. A frozen source/bundle/receiving
packet is preserved through the existing ThinkPad external-contribution intake.
