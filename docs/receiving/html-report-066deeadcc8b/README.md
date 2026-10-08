# Actual-run HTML review for TestPilot

TestPilot now writes `report.html` beside `testpilot.patch`, `report.json`, and
`report.md` after a run. Opening that one HTML file gives a readable review of
the recorded outcome, generated tests, pytest cases and diagnostics, source
selection, repair history, coverage, warnings, and usage ledger. Its patch and
JSON download links contain the exact bytes written by that same invocation.

The document works without a server, JavaScript, browser storage, or remote
assets. Native disclosures, section links, focusable table regions, and print
styles support reviewing long runs at desktop and narrow widths. The recorded
pytest output is explicitly labeled as the **last 3,000 characters**. Missing
JUnit data and missing coverage remain unavailable; a measured zero remains
zero. A retained previous repair result does not imply another test execution.

## Source scope and current-main composition

The source claim is [issue #17](https://github.com/Jacob-Met/testpilot/issues/17).
The implementation adds `testpilot/html_report.py` and a new output key/write in
`testpilot/loop.py::write_outputs`, with one renderer import. Removing those
additions reconstructs each recorded canonical parent loop file byte for byte. The existing
patch, JSON, Markdown, pipeline, sandbox, model configuration, and run parser
are preserved. Nineteen focused tests, two portable author capture drivers,
and a short README usage section accompany the implementation.

| Source boundary | Exact identity |
| --- | --- |
| Canonical baseline | `d7c28b0ad261e78d681f40e355447dffa4d435ed` |
| Canonical baseline tree | `99f94e3c7b0774b04a7e28fa13730b7e464252d6` |
| Local source projection baseline | `4ef553042a2455f509e2c4c943aa10d81ff7e5d3` |
| Independently received local source projection | `fe791af1a0908b2379dd7cbb87a9fb8f3cad87de` |
| First current-source composition base | `dc9735cbbd9c271bdf2bc68656aff1f56d88c0fa` |
| First current-source composition tree | `c79b55004d28ebcd9592dcdd27cb77dd49644f39` |
| Last native-qualified PR20 composition base | `269e55332a9bb78a0a0e107cbab6b2e5c895ca57` |
| Last native-qualified PR20 composition tree | `2045a73704f752d374704657fccf90fd5e774258` |
| Renderer SHA256 | `183703d05f32552f7f7c39aa958c39bae61d824e3fa9cd6a6dd686f0d4c228a4` |
| Original frozen loop SHA256 | `bf19e45239e7301f3b7b1a07ecfb1b80224ac60158c7134190de252b54ac4559` |
| Native-qualified PR20 loop SHA256 | `cdbe364296b8a81ea852a5c70f757db894e52cb9a66db9cc9a6f60b4569d3539` |
| Final publication parent | `3e745e6b6a2f7e383fc6b43f12e69f7a221fb051` |
| Final publication parent tree | `56b8c198f3d88e133c6d641b0cc7c63de0dd6fcd` |
| Final publication loop SHA256 | `41506f3c29febd3b10c4dce43f7f8e0695c32885ddc08e56e1c96d5bb2f212a4` |
| Focused tests SHA256 | `bb2d6b66ecf929ee6340ae6f39875a07e64dd8c5af2053944b16ad93aa7d6f5c` |

The local commits are isolated source projections, not claims of canonical
remote ancestry. The [frozen source manifest](author/candidate-source-manifest.json)
lists all 77 execution files and the six scoped paths. The baseline projection
contains 73 files. Existing evidence, `web-demo/`, and evaluation results are
outside these execution projections; publication preserves those canonical
repository leaves.

During receiving, PR #18 integrated physical-line selection and PR #19 added
the `targets` command. Their only production changes relative to this baseline
are `testpilot/diff.py` and `testpilot/__main__.py`, with two new test files.
None of the six report-scope paths changed upstream. The separate
[79-file current manifest](author/current-source-manifest.json) retains those
four upstream files verbatim and keeps all six frozen report files unchanged.
Every unowned execution-file Git blob matches the complete current tree.
The unchanged author CLI and browser drivers were then run once on that exact
composition. The independent baseline and candidate runs remain attached to
their original source identities.

A later publication check found PR #20, which adds generated pytest
module-name reservation to a different part of the shared loop and one README
bullet. The [native composition supplement](current-composition/README.md)
preserves the entire current allocator and applies only the same accepted
HTML additions. Undoing those additions reconstructs both current parent
files exactly. The other four scoped files are unchanged, and all 74 unowned
files in the 80-file execution projection match current canonical blobs.
Two targeted native CLI cases exercise same-basename generation and partial
repair aliases through the composed report writer; the original author and
independent evidence remains frozen. Its separate independent receiver accepted
all 134 archived members and 80 source files, recomputed 14 HTML tables and 92
data cells, and verified both allocator/repair results and four actual
browser downloads. The [complete PR20 receiving packet](current-composition/independent/README.md)
is preserved unchanged with its portable verifier.

The final parent then integrated PR #21's fresh coverage report destination
and truthful unavailable handling, and PR #10's model response timeout handling.
The [final publication source comparison](publication-parent/README.md)
preserves both canonical files and their new tests as unowned parent leaves.
The shared loop changes only the inherited Markdown coverage-unavailable wording
relative to the native-qualified PR20 loop. Removing the accepted HTML additions
reconstructs current canonical loop and README bytes; all 22 other current loop
definitions and the result schemas are unchanged. This final parent receives a
source reconstruction check and exact-head hosted CI, with no new native
product invocation attributed to it.
The independent receiver also retrieved the final primary commit, complete tree,
and four canonical files directly, then accepted this source-only reconstruction.
Its [separate unchanged addendum](publication-parent/independent/README.md)
preserves that narrower review boundary.

## Observed behavior

All native product invocations below ran on the authorized Mac in private
source and fixture directories. They used Python 3.13.7, pytest 9.1.1,
coverage 7.16.2, Node 26.3.0, Playwright 1.62.1, and actual Chrome
154.0.8037.98. Exact commands, dependency versions, source snapshots, and raw
reports are preserved in the packet.

| Receiving boundary | Result |
| --- | --- |
| Final author focused tests | 19 passed |
| Author actual CLI, unchanged baseline | 9 expected outcomes; no HTML produced |
| Author actual CLI, frozen candidate | 9 expected outcomes; all reports written |
| Detached-document author browser checks | 133 passed, including 18 exact downloads |
| Literal plan/generated-code CLI and browser supplement | 1 actual CLI case and 9 browser checks passed |
| PR18/19 author composition | Same 9 CLI cases and 133 browser checks passed; all 79 source files stable |
| PR20 allocator/report composition | 19 focused tests, 2 targeted CLI cases, 39 unchanged browser checks passed; all 80 source files stable |
| Independent PR20 source and archived evidence receiving | 134 members, 80 source files, 14 HTML tables, 92 data cells, four actual downloads, and both native cases verified |
| Final publication parent | Source-only reconstruction of current loop/README and canonical model/sandbox; hosted checks gate integration |
| Independent actual CLI receiving | 7 cases, 68 checks passed |
| Independent detached-document browser receiving | 7 cases, 219 checks passed; 21 exact downloads |
| Independent original-writer replay | All 21 JSON, Markdown, and patch files matched byte for byte |
| Independent saved-DOM recomputation | 32 tables, 214 data cells, and 25 recorded case/diagnostic appearances matched |
| Independent controlled defects | Changed embedded JSON byte and removed output-tail qualifier were both rejected by the unchanged receiver |

The nine author cases are passing generation, successful repair, failed
generation, suspected code bug, no generated tests, no changes, exhausted
budget, model error, and timeout. They invoke the actual `python -m testpilot
run` command, real pytest and coverage subprocesses, and `git apply --check`
for every nonempty emitted patch. Disposable input repositories are checked
for mutation. The recorded CLI exit remains 0 for a passing outcome and 1
for the other pipeline outcomes.

**These fixtures use explicitly authored ScriptedModel replies.** They exercise
the real CLI, writer, sandbox, generated tests, and browser document. Configured
model names appearing in the ledger are routing labels; they do not establish
provider execution or model quality. No installed TestPilot runtime or user's
application repository was activated as a receiving target.

Each browser run copies the generated HTML into a separate directory before
opening it. Downloaded bytes are compared with that run's original artifacts.
Keyboard navigation, disclosures, narrow tables, actual print PDF output,
offline loading with JavaScript disabled, and application/network error
observations are recorded. The literal supplement puts markup-shaped text and
Unicode into an actual planner response and generated Python comment: the
visible text and downloaded artifacts remain faithful, with no injected
element or external request. The preserved PNGs are actual headless Chrome
captures at CSS viewport sizes, rather than physical-device or screen-reader
qualification.

The independent receiver authored its controls before inspecting candidate
source. Its 21 browser downloads comprise seven JSON and seven patch downloads
in the ordinary contexts, plus seven JSON downloads in separate contexts with
JavaScript disabled. Detached HTML copies are counted as source custody, not
downloads. Its separate 21-file original-writer replay compares outputs produced from each
captured result; it does not assume byte equality between separate CLI runs
whose elapsed times and fixture paths differ. The receiver's own archive,
README, receipt, verifier, raw reports, and initial observer corrections are
preserved unchanged under `independent/`.

## Retained failures and corrections

The initial complete native suite reported **191 passed and 5 failed**. All
five failing tests were replayed against the unchanged 73-file baseline and
failed there as well. Two existing collection assertions fail in this setup;
the evidence does not assign an unproved cause. Three raw-filename tests fail
on APFS with `OSError: [Errno 92] Illegal byte sequence` before report output.
Exact test IDs, both full failure captures, and command exits are recorded in
[the author receipt](author/author-receipt.json).

That full-suite run used the preserved pre-phone renderer. The later source
change adjusts table CSS and table-region markup after visual inspection
found cramped phone ledger columns despite a passing overflow check. All
19 focused tests, nine CLI cases, and 133 browser checks were repeated on the
final frozen source. The original renderer and both sets of screenshots and
browser reports remain available. This record does not claim a completely
passing native full suite or a final full-suite rerun.

The first author CLI observer supplied an empty ScriptedModel response
directory for `no_changes`. Client construction returned configuration exit 2,
and the observer then attempted to read a nonexistent report. The fixture was
corrected to supply one unused response; an empty diff still makes no model
call. The original driver and failure are retained separately from the
completed nine-case runs. Independent observer corrections and storage
recovery are attributed in the independent packet rather than counted as
product failures or new product tests.

## Inspect and replay

[The native author archive](author/author-native.tar.xz) contains 837 ordinary
members: the exact baseline, original candidate, current composition,
fixtures, commands, outputs, screenshots, PDFs, and prior failure captures.
[Its manifest](author/author-native-manifest.json) lists the other 836 members
by size and SHA256. The archive SHA256 is
`38427d84487956f1296cdca9b65bd3178fbc661be17a0c9b1174d9dcab99f725`.
Dependencies, disposable Git metadata, and caches are excluded.

Run the portable verifier without invoking generated tests or a browser:

```sh
python3 -B docs/receiving/html-report-066deeadcc8b/author/verify_author.py
```

Its output must match [verification.json](author/verification.json). The
verifier checks every archive artifact, all three source closures, the six
unchanged scoped files, current upstream Git blobs, fixed CLI cohorts,
embedded and actual downloaded bytes, browser report bindings and outcomes,
and the preserved baseline failures. It verifies saved evidence; it does not
claim to repeat the native observations.

To repeat the product boundary, use a fresh source checkout and an interpreter
with the declared test dependencies. Choose new, absent output directories:

```sh
python -B docs/receiving/html-report-066deeadcc8b/capture_runs.py \
  --source /path/to/testpilot --python /path/to/testpilot-python \
  --output /path/to/new-cli-capture --expect-html

TESTPILOT_PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs \
TESTPILOT_BROWSER_EXECUTABLE=/path/to/chrome \
node docs/receiving/html-report-066deeadcc8b/check_browser.mjs \
  /path/to/new-cli-capture /path/to/new-browser-capture
```

The browser driver can also resolve an installed `playwright` package when
the module variable is omitted. The archive retains the separate literal
supplement and historical absolute native command paths for provenance.

## Actual final document captures

[Desktop repair report](author/preview-desktop.png) ·
[375px repair report with keyboard-scrollable ledger](author/preview-phone.png)

These two exposed images are byte-identical copies of the corresponding final
native archive members. They make visual review possible without expanding
the complete packet.
