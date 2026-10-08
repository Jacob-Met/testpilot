# R3: final current-main composition and independent review

Publication parent: `aded01e114080c0bbc9d273f240c6bc2c5119694`, full tree `72d8060994dc1a01be240121cecd146c2bf622b3`.

The five owned product paths are byte-identical to accepted R2. The later accepted PR22 adds only generation fence/patch production logic in `testpilot/loop.py`, along with its own regressions and receipts. We receive that complete exact upstream blob, preserving the PR23 collector, PR24 HTML output and every other current-parent leaf and mode.

`source-composition.json` pins the native source, product tree, unchanged owned inputs, exact materialized owner inputs, full incoming delta and immutable R1/R2 archive hashes. The original parent tree was independently reconstructed from all 908 leaves before applying our changes; all 906 unowned leaves are retained. `incoming-loop.diff` and `static-composition.stdout` show that the only changed top-level AST definitions are `_FENCE` and `make_patch`. Recheck imports the existing sandbox; its CLI dispatch returns before model construction. No product process or test suite was executed for this later source-only composition.

The first static helper used incorrect assumed CLI identifier names and stopped with a ValueError. Its retained stderr is `initial-static-harness.stderr`; the corrected helper reads the actual `a.cmd`/`make_client` source. This was a qualification-helper error after the separate R3 copy was prepared, with no product execution. The original helper remains in the native evidence root.

## Independent acceptance

`root-source-review-r2.json` records complete source/API/CLI/sandbox/guide/test acceptance. `root-independent-receipt.json` preserves two actual independent CLI executions on candidate-r2. Only a disposable report's historical success metadata was forged; its exact retained tests still returned current buggy exit 1 with three failures/one pass and fixed exit 0 with four passes. Original and disposable reports, author/reviewer fixtures and source hashes remained unchanged; both calls recorded zero model calls.

Those executions remain R2 evidence, as does the authored affected-case and three-control follow-up. R1's 57 tests, six subtests and existing optional coverage skip remain tied to its original source. Current hosted CI is a separate gate. The native source and both complete prior archives are retained under `/home/jacob/testpilot-recheck-68e476e98b77`.
