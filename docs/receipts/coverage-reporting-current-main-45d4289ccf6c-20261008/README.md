# Coverage report retention on current TestPilot main

## Current scope

This contribution qualifies the independent coverage-report retention fix. The existing-main generated-attribution defect reported by receiver965d remains with collection owner86776 and that receiver. Its repair is separate from this coverage delta.

The earlier frozen composition packet records a provisional blanket integration hold. The current decision narrows that disposition: the independent coverage fix can proceed while preserving collection behavior outside its accepted report block. The original negative, reviewer conclusions and historical manifests remain unchanged. This document states the current publication scope.

## Exact source

Accepted coverage history `fd77eb028bdbdba35644b44c524471b6413fad39`, original PR14 `dcd353531ad3dde353b63db4b09adca976b9f256`, and current main `9efb47561544db608613d7055f5f1226b2d7f7e7` remain ancestors of this native composition. Current main includes the separately owned decoder from PR15 and physical-line selector from PR18.

Before these four current-receipt files, source component tree `000610b046b7b4921d1e96b882231ea288e03430` has 685 leaves. All 397 current-main leaves outside the two reviewed runtime files are exact, including decoder, collection runner, tests, workflow and evidence.

| Path | SHA256 |
| --- | --- |
| `testpilot/sandbox.py` | `2e852248ffc238371cf2b11b5797a88c519330db359b2cb969bc61aa72ef1931` |
| `testpilot/loop.py` | `dea26d8eeec2364d3dbb702671b579ae3890881d866a76ab9d98dfe2992decee` |
| `testpilot/_pytest_generated.py` | `8168919730b2ef480f34ea54095caaa11dbb785dd60d7390c59bf11fb1362dcc` |
| `tests/test_coverage_reporting.py` | `49c273ba51487a02c8c5b2bccbac1522980bec0f83fad5f854aded868fab7ede` |

The independent review verifies that sandbox differs from original PR14 only in the accepted coverage block, retaining collection/provenance parsing and the `generated_files, junit_available` return. Loop differs only in unavailable-report wording.

## Receiving

The real CLI defect is a valid 75% JSON report returning exit 2 under configured `fail_under`: rejecting it inflated a later 100% result to a 100-point gain. The fix receives that report and measures the actual 25-point gain. It reserves the report destination after pytest and preserves unavailable status for missing or failed reporting. Original receiving passed seven new controls plus 21 existing controls, including stale-report rejection, and the actual CLI pair.

Material composition tree `08d13653668d58660cbf3614108ba79ddd8f3b17` was received once through the complete then-configured 15-module suite: 165 passed and four environment assertions failed. The selected interpreters had pytest but lacked coverage. Actual probes and the resulting `coverage: null` reports are retained. Aligning only the private receiving environment with the same installed package bytes made those four unchanged controls pass. Sources were identical across runs and sandbox temporary directories were empty.

The outcome remains **165/4 plus a bounded 4/4 correction**, rather than a single-environment full green run. The independently reviewed runtime/test pins above remain unchanged. The later decoder and physical-line selector source, tests and evidence are disjoint and preserved. The existing hosted workflow must exercise the full current published tree, with coverage installed, before final integration.

## Existing collection finding

[Issue13 comment6059045816](https://github.com/Jacob-Met/testpilot/issues/13#issuecomment-6059045816) preserves receiver965d's 7-pass/4-failure attribution result, including an ordinary CLI case where pre-existing metadata qualifies an unexecuted generated file. Current main retains that original PR14 implementation. This coverage contribution neither changes it nor claims acceptance of the whole collection subsystem. The original owner and receiver retain that correction scope; no duplicate attribution tests or competing correction were introduced.

Original coverage and composition packets remain under their existing receipt directories. `native-preparation.json` binds preservation, `scope-disposition.json` records the current scope, and `artifact-manifest.json` binds this three-file payload.
