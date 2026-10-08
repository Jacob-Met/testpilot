# Preserve generated Python during extraction and patch export

Valid generated Python could be truncated at an inline triple-backtick string, or produce a corrupt Git patch after pytest had passed. This contribution receives the two remaining bounded repairs in the generation pipeline.

## Product scope and current parent

| Boundary | Change | Failure repaired |
| --- | --- | --- |
| Generated Python block | Closing fences start a line; standalone and legacy adjacent blocks are supported | Inline backticks truncated valid generated tests |
| Exported patch | LF-delimited old/new lines retain their endings | Passing tests produced corrupt Git hunks |

Only `testpilot/loop.py::_FENCE` and `make_patch` change. The two new regression files are `tests/test_fenced_code_boundaries.py` and `tests/test_patch_physical_lines.py`.

The receiving base is `3e745e6b6a2f7e383fc6b43f12e69f7a221fb051`, tree `56b8c198f3d88e133c6d641b0cc7c63de0dd6fcd`. Current baseline loop `328221e1556b986b75c6e61f30eef8dc0f3d8961` contains the separately merged module allocator and report wording. The corrected receiving loop is Git blob `129f6b1db17ef62eb0462665191d79dac8886413`, SHA-256 `fbe16f8c79fb5acc1d27fe2c608ee62c3a9648770afbc5e2cb54ff5c130962ca`. The initial submission transferred the accepted `_FENCE` and `make_patch` segments from historical loop `c97d857e34d9fd93e53251edac0a0dbf6c9de07f`. Submitted-head CI then exposed the compact-fence compatibility regression described below. The correction changes only `_FENCE` from that submission; `make_patch` and every other current loop byte remain intact.

PR 18 has already integrated the physical-line selector and `tests/test_physical_lines.py`. This contribution inherits that owner's source, including PR 15's encoding support: `diff.py` blob `f92280a9ad3f9f79713dce7ba7ae28c55414783a`; existing selector test blob `d25916fd9bc0cf98647e2678ce942fa6f2d2ba1c`. Our unpublished selector and its same-named test are removed from the product payload. The original selector receipts below are retained as historical independent work; they do not claim ownership or new execution of the integrated source.

The [initial receiving scope](receiving-scope.json) remains frozen for the first submitted source; the [compatibility receiving scope](fence-compatibility/receiving-scope.json) records the corrected fence and exact receiving boundary. All 727 other original current-parent leaves remain unchanged. The inherited source includes model timeout PR 10, selector PR 18 with PR 15 decoding, CLI preview PR 19, module allocation PR 20 and coverage/report PR 21. Their implementations and ownership are preserved.

## Submitted-head compatibility correction

The first submitted head `c138a7992fa35066d115dee6e8fddef33496b54c` ran the real hosted suite in [run 37780846512](https://github.com/Jacob-Met/testpilot/actions/runs/37780846512): **2 failed, 248 passed, 6 subtests passed**. The two unchanged preservation tests concatenate a closing fence directly with the next opening fence. The original standalone-only closer treated this six-backtick boundary as code and bypassed the conflicting-repair-block check. This was a regression in the first contribution, and its [failure receipt](fence-compatibility/hosted-failure.json) is preserved.

The revised closing expression accepts that existing compact boundary at the start of a line while preserving inline Python backticks. Both actual failing tests retain their expectations. Two explicit compact-block order cases are added to the existing new fence regression file.

The targeted native run retains the twelve prior parser controls and executes both new compact-order cases plus the two actual hosted-failure consumers. The published baseline gives **4 failures / 12 passes**; the revised candidate gives **16/16 passes**, zero errors or skips. All current source and test bytes are unchanged by execution. [Exact commands and results](fence-compatibility/native-results.json) are separate from every historical qualification below. The [independent revised-source receiver](fence-compatibility/independent/REVIEW.md) also accepts the exact corrected loop: two LF/CRLF parser controls, indented adjacent boundaries, a longer final close, and an inline six-backtick/U+2029 literal. Its actual public CLI changes from failed to passed, preserves the existing filename through its normal alias, applies the exact generated patch, and passes three receiving pytest cases. All seven source modules and original fixture files remain unchanged. Final-head hosted CI remains required before integration.

To replay that targeted run, place `run_controls.py` beside sparse `baseline/` and `candidate/` source directories. Both receive the eight unchanged files named in `source-receiving-pins.json` and the corrected `tests/test_fenced_code_boundaries.py`; use the initial `c138a799` loop in `baseline/` and the corrected published loop in `candidate/`. Run `python3 -B run_controls.py` with native pytest and Git available. The driver executes only the two declared test selections, checks the source hashes after execution and retains its own raw receipts. The two complete repository baselines are not duplicated here.

## Frozen component qualification

| Component | Original new cases | Candidate new plus selected existing cases | Independent receiving |
| --- | --- | --- | --- |
| Physical patch lines | 11 fail / 4 pass | 17/17 | Real TestPilot/Git/apply/pytest consumer passes; original emitted patch is corrupt |
| Closing-fence boundaries | 7 fail / 5 pass | 13/13 | Two methods pass; original has two failures and truncated generated code |
| Historical source selector, superseded by PR 18 | 6 fail / 5 pass | 17/17 | Three methods pass; original has 17 failed assertions within those methods |

These are distinct frozen runs with zero candidate errors or skips, not one aggregated suite total. The component directories retain exact compact author results and unchanged independent executables/results. Their original source parents and native raw-receipt hashes are recorded; complete baseline packages are not copied into this contribution.

## Combined receiving and its exact boundary

The independent public CLI receiver runs authored scripted responses through real native Python, Git and pytest. It retains raw Unicode separators and inline backticks, while an existing generated-test filename forces the collision alias.

All fifteen assertions pass on the separately pinned PR 14 composition: CLI exit 0/status `passed`; two generated tests and three pytest passes; exact selected-source report and line identity; retained existing test; Git validation/application 0; applied generated bytes exactly matching the authored reply; then three receiving pytest passes. Original source and existing test bytes stay unchanged before and after application. All eleven qualified inputs retain their hashes. Default coverage reports 75% to 100% for this authored fixture only.

The [47a independent acceptance](combined-current/REVIEW.md), [result](combined-current/combined-results.json) and [composition](current-composition.json) establish compatibility with PR 14's collection plugin and sandbox. They use our historical selector `ea74d79d2789919a7a87bff745e3b6bed12e38a7`. The integrated PR 18 selector and later independently received runtime additions are inherited unchanged; those older executions are not relabeled as fresh runs on 9ef or 3e745e6b. The public report checks selected-source bytes; the separate historical selector receiver checks actual planner-message source.

The original [f1a8 composition](composition.json), [combined result](combined/combined-results.json) and [independent executable](combined/receive_combined.py) remain frozen. The 47a run changes only the executable's recorded parent metadata; the [one-line patch](combined-current/harness-metadata.patch) reproduces that difference. Commands and fifteen assertions are unchanged. Its executable SHA-256 is `54012a5e1468d856468d549a935d02a54dfb2cff808a8510cfba8639fb78b27e`.

## Replaying focused checks

```bash
python3 -m pytest -q tests/test_patch_physical_lines.py tests/test_fenced_code_boundaries.py
```

The component receipts name the commands actually executed. Each independent component executable accepts a source directory and output receipt path. To recreate the recorded 47a combined run, copy the original executable into a fresh disposable directory, apply the metadata patch, copy its source-manifest.json, and supply the exact qualified checkout at the sibling source/ path. Use Python with the project's test dependencies. The receiver creates its own combined-consumer/ fixture and requires a fresh directory.

Archived executables are retained under `docs/receipts/` with names such as `independent_review.py` and `receive_combined.py`, outside the default pytest filename patterns. Current `pyproject.toml` keeps `testpaths = ["tests"]`; this contribution changes neither its collection configuration nor the workflow. Only the two declared regression files enter maintained test discovery.

The existing hosted CI is the required final receiving gate for the submitted current source. The fence change retains the opening-fence grammar; it is not a complete Markdown parser. The patch change does not introduce new unterminated-file or modified-CRLF behavior. No provider-quality, installed-runtime or new full-suite claim is inferred. Model-timeout PR 10 remains a separate contribution.
