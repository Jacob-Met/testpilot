# TestPilot HTML report: independent receiving

**Decision: accepted for the exact reviewed source. No supported-path implementation blocker was found.**

This is the independent receiving packet authored by `/root/research_execution` for
[Jacob-Met/testpilot issue #17](https://github.com/Jacob-Met/testpilot/issues/17).
The receiving scope was claimed before candidate inspection in
[comment 6059391380](https://github.com/Jacob-Met/testpilot/issues/17#issuecomment-6059391380).
The product implementation and its author qualification belong to
`/root/product_execution`; those results are not counted as independent results here.

## Exact source and scope

| Item | Identity |
| --- | --- |
| Canonical baseline | `d7c28b0ad261e78d681f40e355447dffa4d435ed` |
| Baseline tree | `99f94e3c7b0774b04a7e28fa13730b7e464252d6` |
| Reviewed candidate projection | `fe791af1a0908b2379dd7cbb87a9fb8f3cad87de` |
| Renderer SHA256 | `183703d05f32552f7f7c39aa958c39bae61d824e3fa9cd6a6dd686f0d4c228a4` |
| Loop SHA256 | `bf19e45239e7301f3b7b1a07ecfb1b80224ac60158c7134190de252b54ac4559` |

The packet includes the complete 73-file baseline source/config/test/evaluation-input
projection and the complete 77-file candidate projection. The original repository
tree contains 362 ordinary leaves; historical documentation, web-demo and previous
evaluation results were outside this executable projection. Every baseline source
file is bound to its exact canonical Git blob, byte count and mode in
`canonical-tree.json` and `baseline-source-manifest.json`. No AGENTS.md was present.

There are exactly six scoped paths: README, loop, the new renderer, its new unit
tests, and two author receiving drivers. Seventy-one inherited files remain exact.
The loop adds the renderer import, the HTML path, and one HTML write after reading
the exact newly written JSON/patch bytes. Its other 20 top-level function/class
definitions, including the runner, result schema and Markdown renderer, are
unchanged. `source-review.json` contains the exact two existing-file diffs.

The author later reported upstream PR18/PR19 changes to the CLI entry point and
physical-line selector. This packet qualifies the original exact projection above.
A later current-source composition and its author compatibility runs belong in a
separate supplement; they are not silently substituted for this reviewed source.

## Independent execution results

All receiver fixture code and the CLI/browser/original-writer controls were authored
before candidate inspection. The final control hashes and the pre-inspection
boundary are recorded in `final/controls-freeze.json`.

The actual runtime was macOS 26.6.2 arm64, Python 3.13.7, pytest 9.1.1, coverage
7.16.2, Node 26.3.0 and installed Chrome 154.0.8037.98. The author-declared Python
environment was reused read-only with bytecode writes disabled. All source copies,
authored repositories, outputs and browser contexts were independent and private.
Only the scripted model backend ran; no provider request was made.

| Actual CLI case | Recorded outcome | Exit |
| --- | --- | --- |
| Unicode source, parameterized cases and one skip | passed | 0 |
| Collision mapping and partial repair retaining the other file | passed | 0 |
| Scripted model flags a possible code bug | suspected_code_bug | 1 |
| Real process timeout with a bounded output tail | failed | 1 |
| Generated tests all skipped, with an existing test passing | no_tests | 1 |
| Empty diff | no_changes | 1 |
| Scripted editor response exhausted | model_error | 1 |

The corrected baseline reaches all seven intended outcomes and fails only because
it emits no HTML. The candidate passes **7 actual CLI cases / 68 checks**. Actual
child PIDs, argv, exits, logs and before/after source snapshots are preserved.
The timeout has no return code or JUnit/coverage result and stores exactly 3,000
characters: the emitted tail marker is present and the earlier output marker is
absent.

For each captured candidate result, the independent replay reconstructs the
original LoopResult and invokes the untouched original writer. **All 21 original
JSON, Markdown and patch files are byte-identical.** This compares the same captured
result, avoiding a false equality claim about separate runs with different timings
or temporary paths.

The unchanged browser driver opens only a detached copy of each actual HTML file,
with no sibling artifacts. It passes **7 cases / 219 checks**: native navigation and
disclosures, literal text and source, recorded failure messages, unknown values,
retained-output qualification, 375 px page containment, no document network
requests or application errors, and exact downloads. **All 21 actual downloaded
files match the originals:** 14 normal JSON/patch downloads and 7 additional JSON
downloads with JavaScript disabled. Native print output is preserved as an
eight-page PDF; the main receiver printed after opening disclosures for inspection.

A separate standard-library recomputation confirms every cell in the **32 actual
DOM tables / 214 data cells**, including final/per-round counts, coverage and the
ordered model/token ledger. It also checks 25 recorded case identity/diagnostic
appearances, all source/receipt/file bindings, output bytes and fixture outcomes.
These counts describe this authored experiment, not general model performance or
test quality.

## Consequential negative controls

The original candidate HTML and source remain unchanged. Two copies of actual
documents were deliberately altered, and the exact unchanged browser receiver
rejected them with only the intended failures:

- Appending one valid JSON whitespace byte to the embedded JSON download fails
  both normal and JavaScript-disabled byte equality, despite unchanged visible
  report content and unchanged sibling JSON.
- Removing only the final/per-round retained-output qualifier fails the output-tail
  check, while original JSON/patch/output bytes and all other checks remain intact.

`final/negative-controls/` preserves the mutations, exact source/mutant hashes,
all derivative artifacts, actual browser child exit 1 and the exact failure sets.
No TestPilot generation ran for these controls.

## Preserved preparation and observation limits

The initial timeout fixture attempted `pytest.ini addopts=-s`. The canonical
sandbox intentionally clears addopts, so the print remained captured and the
receiver correctly failed its tail expectation. The untouched initial inputs,
preparation script and seven original reports/logs remain at the packet root.
`prepare_inputs_v2.py` fixes only the authored fixture by explicitly releasing
pytest capture. The corrected final inputs are separate under `final/`, and were
verified on baseline before candidate execution.

One initial post-resize mobile screenshot shows a repeated-looking header near its
lower edge. The actual DOM and serialized HTML contain one header. The original
image remains intact. Three fresh 375 px browser contexts, with fonts/layout
settled before capture, show the unchanged documents without that duplication;
their DOM geometry, screenshots and keyboard table-scroll result are in
`final/visual-supplement/`. This is preserved as an observation/capture limit, with
no implementation edit inferred or made.

The first portable-verifier preparation assumed the candidate manifest's
`bytes/git_blob` field names for both manifests. The canonical baseline uses
`size/sha`. Its failed version and actual exit-1 tool record are retained. The
successor only normalizes those field names and then recomputes the same evidence.
No browser/CLI expectation was changed after candidate inspection.

Primary-workspace Python lacked pytest during dependency discovery; no local
TestPilot qualification was started there. Mac metadata writes later hit ENOSPC,
and a shell heredoc could not start. Executed product evidence was already complete.
Only this receiver's reproducible, completed Suite dependency cache was reclaimed;
Playwright's 173 retained files were checked unchanged, and all source, lockfiles
and evidence remain preserved. The preparation/resource notes are included.

This receiver does not claim that passing tests prove correctness, that a scripted
diagnosis finds a real bug, that recorded coverage measures assertion quality, or
that estimated/unpriced ledger entries are measured billing. The HTML's downloads
preserve the actual artifact bytes. No production service, clipboard, model,
deployment or repository application of generated patches was exercised.

## Packet layout and verification

- `baseline/`, `candidate/`, manifests and `canonical-tree.json`: exact source custody.
- Root `inputs/`, `baseline-cli/` and launch records: original fixture attempt.
- `final/inputs/`, `final/baseline-cli/`, `final/candidate-cli/`: final authored inputs and actual CLI evidence.
- `final/original-writer/`: all seven original-writer replays.
- `final/*-browser/`: detached HTML, actual downloads, DOM captures, PNGs and PDF.
- `final/negative-controls/`, `final/visual-supplement/`: the two independent supplements.
- `verify_review.py`, `verification.json`: portable recomputation and exact expected output.
- `receipt.json`: every other frozen member's byte count and SHA256.

After extracting this packet, run from its root with Python 3.10 or newer:

```sh
python3 -B verify_review.py > /tmp/testpilot-review-verification.json
cmp verification.json /tmp/testpilot-review-verification.json
```

The verifier uses only the standard library, verifies every receipt-listed member
when the receipt is present, and recomputes the captured evidence without running
a browser, generated test, provider or TestPilot. The original scripts retain exact
native commands/paths as provenance. A fresh execution replay requires a new private
output root, equivalent declared dependencies and an adjusted local Chrome/Playwright
path; never overwrite the frozen evidence.
