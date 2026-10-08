# Independent review: coverage and generated-test collection composition

## Decision

Accept the exact prospective native source commit `09656db720176124bd206ed4bb871e6e8dcf6d42`, tree `08d13653668d58660cbf3614108ba79ddd8f3b17`, for the recorded native composition scope. This receipt belongs to `chatgpt-45d4289ccf6c/native_execution`.

The source has two parents: our previously qualified coverage source/evidence `fd77eb028bdbdba35644b44c524471b6413fad39` and the original collection owner's published PR14 head `dcd353531ad3dde353b63db4b09adca976b9f256`. The collection owner and its separate receiver retain their authority. Their adoption or replacement disposition and an actual final-headed hosted gate remain pending.

## Source custody

The reviewer read all 451 immutable combined-tree blobs and verified modes, Git blob identities, lengths and SHA-256 values against the source manifest. All 349 owner leaves remain present. The only owner-leaf changes are `testpilot/sandbox.py` and `testpilot/loop.py`. The 102 coverage test, documentation and historical evidence leaves are exact copies of the previously qualified coverage branch.

An AST comparison against PR14 proves that removing the specifically reviewed coverage-report block and report wording leaves identical runtime ASTs. The new report block itself is identical to the previously qualified coverage change. It allocates the output destination after pytest, accepts a present report after exit 0 or 2, and keeps genuinely unavailable coverage unavailable. The collection owner's `generated_files` and `junit_available` return arguments, generated-test custody, collection logic and other runtime behavior are preserved.

This is fresh review of the combined source. Earlier standalone coverage acceptance and the collection owner's prior acceptance are retained as ancestry, without being represented as acceptance of these combined bytes.

## Native execution evidence

The original full run remains **169 cases: 165 passed, four failed, zero errors or skips**, using the existing outer Python 3.14.4 environment. Raw JUnit independently confirms the count. All seven coverage cases, 15 owner collection cases, 11 independent collection cases, eight sandbox cases and 13 loop cases passed.

The four failures were the unchanged selected-interpreter test's absolute, relative, PATH and symlink-parent cases. The fixture shares the directory containing pytest. In the original environment that directory was the system package directory, while coverage was in the outer virtual environment. Each selected interpreter reported `No module named coverage`; the outer test then asserted coverage availability based on its own interpreter.

The actual CLI reports correctly recorded unavailable coverage, successful repair, two passing final tests, one generated test and available JUnit. This was a real failed full-gate observation with a specific receiving-environment cause, and it is preserved.

The author corrected only an exclusive receiving environment. It physically copied the unchanged pytest package so its resolved parent became the shared private tooling directory, and used private links to the existing coverage and supporting packages. The reviewer independently verified all **499 recorded package payload files** against both original and receiving locations. No packages were downloaded or installed, and the existing environments were not edited. Two intermediate setup failures are retained.

Exactly the original four failing parametrizations were then run, with **four passes, no failures/errors/skips**. Their raw JUnit case set equals the original failure set. Every source hash, including the test file, matches the initial run. All four raw CLI reports show 100% changed-line coverage, two final passes, one collected/passing generated test, and available JUnit. Each has five actual execution markers in its selected virtual environment. Original and corrected patch bytes match. Both runs record empty sandbox temporary roots after execution.

The resulting qualification is **165 passes in the initial full run plus four targeted passes in an aligned environment**, with the initial four failures preserved. It is not a single-environment 169-pass rerun, and it is not a hosted gate.

## Boundaries and reproducibility

No tests were executed by this reviewer. The reviewer read immutable source objects, unchanged test/fixture code, original execution logs, JUnit, runtime manifests and actual CLI reports/markers. No owner/source/test/runtime file was modified. A reviewer-side parser initially expected unavailable coverage as a dictionary; the raw report uses JSON null. That reader assumption and its correction are recorded separately and did not change or execute product code.

`source-and-negative-review.json` binds the source and first run; `aligned-four-case-review.json` binds the corrected run and runtime custody; `final-review.json` binds the immutable source commit and frozen author handoff manifest. The artifact manifest covers all retained reviewer files. Original evidence is retained without rewriting its manifests.
