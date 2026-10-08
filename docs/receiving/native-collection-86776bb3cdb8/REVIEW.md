# TestPilot native collection compatibility receiving

The existing generated-file helper can report success on supported pytest 8.0.0 while omitting an existing failing test. The correction is confined to `testpilot/_pytest_generated.py`; it preserves the native configured suite and generated-file provenance without replacing pytest's collector or changing `sandbox.py::run_pytest`.

## Source and ownership

The investigation began against adopted collection main `47a197fd46b107a797b1547db02cb5ed5ad2abe1` and encoding successor `d7c28b0ad261e78d681f40e355447dffa4d435ed`. Independent real CLI receiving used [`269e55332a9bb78a0a0e107cbab6b2e5c895ca57`](https://github.com/Jacob-Met/testpilot/commit/269e55332a9bb78a0a0e107cbab6b2e5c895ca57), complete tree `2045a73704f752d374704657fccf90fd5e774258`, with 432 leaves. The helper and sandbox blobs are identical across those parents. The newer module-identity, target-preview and source-decoding changes were preserved in that receiving copy.

The maintained helper has SHA256 `d65352d7bade965d7b9dc73efe5d4d01844fa8c7474a1bdcdb3b708f6decf768` and Git blob `90b82725bc0eb1ff3d7cb517c4c9dedcfd14bdcc`. The new 17-case portable regression file has SHA256 `011d5c8746d5606d11817a294dd6d699610068982f84076f2824f2321a38f3a3`. `helper-correction.patch` changes only the existing helper; `source-preservation.json` records the unchanged source and the clear new test path.

These controls were independently reconstructed after reading [the other worker's collector claim](https://github.com/Jacob-Met/testpilot/issues/2#issuecomment-6058800140). Its final v3 source and exact peer portable controls were not available in the examined primary or shared artifacts. This packet does not claim to contain or execute those originals. The held `sandbox.py::run_pytest` span and the other worker's proposed collector remain untouched. Root owns coordination and publication.

## Confirmed behavior

A synthetic configured `tests` directory contains an existing `assert False` test. TestPilot adds a passing generated file in the same directory. The adopted helper returns `ok=true`, one pass and zero failures on pytest 8.0.0. Native directory-only collection retains the failing test. Native directory plus explicit generated-child arguments omit it, whether the child is first or last and whether the directory is absolute or relative. Explicit separate leaf paths retain it. Exact inputs and outputs are retained in the selection diagnostic and argument-order controls.

The installed pytest 8.0.0 source caches a directory's collection report while resolving the explicit child, then skips that cached directory during recursive item generation. Newer pytest normalizes overlapping arguments; a custom-named generated file below an ignored directory can consequently lose its explicit-path status and disappear from collection. The latter omission was reproduced on pytest 9.1.1 as zero qualifying generated cases, not a passing generation.

The originally reported hook and same-nodeid defects were not reproduced in the adopted implementation: the native function/class hooks remained once per definition, and both a module doctest and same-named Python test survived with their separate failures. The independent controls exposed the distinct configured-suite omission above.

## Correction

The helper resolves existing named-package arguments through pytest's own `search_pypath`, retaining its available namespace-package option. An explicit generated-module selector is therefore recognized as already selected instead of being broadened to the complete file.

Generated files already beneath a selected directory are not appended as overlapping argv entries. At the native Session collection-start hook, their paths and ancestors retain pytest's explicit-path status. Normal directory traversal, `python_files`, ignore hooks, package collection, conftests, parametrization, selectors and assertion rewriting continue through pytest. Generated paths outside the selected roots are still appended. There is no item/nodeid deduplication or replacement collection loop.

The helper uses pytest's existing initial-path sets and native named-package resolver. Compatibility is directly qualified on pytest 8.0.0 and 9.1.1, both with Python 3.12.14. The package declares `pytest>=8`; this patch does not alter that dependency. Native implementation files and resolver signatures are pinned in `native-compatibility-receipt.json`. No claim is made for every future pytest or arbitrary third-party collector.

## Native qualification

| Source | pytest 8.0.0 | pytest 9.1.1 |
| --- | --- | --- |
| Adopted helper, first 15 controls | 6 passed, 9 failed | 14 passed, 1 failed |
| Adopted helper, two distinct named-package controls | 0 passed, 2 failed | 1 passed, 1 failed |
| Candidate A, first 15 controls | 15 passed | 15 passed |
| Candidate A, named-package controls | 0 passed, 2 failed | 1 passed, 1 failed |
| Frozen correction, all 17 controls | 17 passed, no skips | 17 passed, no skips |

The failed candidate is retained with exact source, raw logs and JUnit. The final controls cover failing existing tests, four separate function/method identities, package roots, custom generated names beneath ignored parents, ignored siblings, explicit filesystem and named-module selectors, keyword/deselect/custom selection hooks, both failure directions for the identical-nodeid doctest/Python pair, and valid empty JUnit reports. Every actual native test input, generated file, argument and result is embedded in the raw logs. No mocked pytest, old suite or provider call is used.

Ruff passes from the actual candidate package root. An earlier check from outside that package requested only import grouping; the proper package-root check passes the unchanged source. The sandbox, generated JUnit property, result schema, absent-versus-empty report behavior and caller/count code remain exact current-main blobs.

## Independent current-main CLI receiving

The product worker independently reviewed the helper and ran the real scripted CLI on exact current main `269e5533` and the frozen correction, using native pytest 8.0.0 with coverage 7.16.2. Its first generated parametrized test fails. The first repair makes the generated cases pass by changing a module constant, which breaks an existing suite contract. Current main incorrectly stops after that repair and accepts the bad patch because the existing contract was omitted.

The corrected helper retains the failing existing contract, requests the second repair, and finishes with three passes: one existing case and two generated cases. The report keeps `tests_written=2`; all seven raw native JUnit reports preserve the expected per-case generated-source properties and project fixture continuity. The original project and all source files are unchanged. The project observer archives completed native XML without changing collection or outcomes.

This separate receiving gate found no source defect. Its 28-file packet is copied byte-for-byte under `peer-cli/`, including the original fixture/scripts, actual CLI reports/logs and raw JUnit. The peer receipt SHA256 is `879068102debf4b8c82d48fa055bd51911670aaeccde1bca137b3a3701f4908d`; its original manifest SHA256 is `4a9669808593e514841f07be280fb769d6d9d2bd51f80c6a122be8819e28810e`. The 17-case matrix was not repeated for this handoff.

## Latest-parent preservation

Immediately before handoff, coverage PR21 advanced main to [`05aab727498df2af27dc6fff17d9375d76c57900`](https://github.com/Jacob-Met/testpilot/commit/05aab727498df2af27dc6fff17d9375d76c57900), complete tree `be8dcf0683a5a9374f67c4b94437fa37c67d484e`, with 722 leaves. The publication payload uses this parent and preserves its complete coverage contribution.

The only changes to earlier production files are post-pytest coverage JSON freshness/report handling in `sandbox.py` and one unavailable-coverage display string in `loop.py`. The entire pytest invocation/collection/JUnit prefix and final result construction remain byte-exact; every other sandbox definition and the loop's repair/count logic are unchanged. Our helper's old blob and all new contribution-path guards also remain clear. `current-parent-disposition.json` and the exact two-file upstream delta record this static extension.

This extension preserves all 290 added coverage/test/evidence leaves and both modified coverage source files. It does not claim new native execution on `05aab727`; the native matrix and independent CLI receipts retain their exact earlier source pins. Root independently reviewed the helper/native collectors and accepted this bounded static extension. Full hosted CI remains the publication gate.

## Scope and reproduction

The current-main staging copy contains all seven native TestPilot Python files plus the exact project configuration, test conftest and CI workflow. It is not a materialized full repository or a full-suite qualification. CI's complete suite remains a publication gate.

Run the portable test from a full receiving repository with its selected interpreter:

```sh
python -B -m pytest -q -s tests/test_generated_collection_compatibility.py
```

The control invokes real child pytest through that interpreter. The raw receipt records the actual native executable paths and exact versions used here. Set `PYTHONPATH` explicitly when using these isolated staging copies so an editable install cannot select another checkout.

Only this receiver's completed temporary test projects were removed after their exact inputs and results had been retained. All failed candidate sources, negative controls, final sources and raw receipts remain available. No owner branch, shared runtime or other worker's directory was changed.
