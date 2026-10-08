# Independent TestPilot preservation review

Reviewer: `ultra-20b27c2e-20261008/runtime_integration`.

The review used an isolated byte-verified copy of `Jacob-Met/testpilot` based on commit `a565cc365fdf9cf346b6104a6abdd77d0b12d2fd`. The implementation under review was `testpilot/loop.py` SHA-256 `dd79fbfbdcab00978b288835645c1b5adf37fec404ec0fa6da0ac41d45a79cbf`. The owner's added test file was SHA-256 `f6efd91dc4554a6cc0d1c162ae41aeec25dc94d81bad3cc5c7cd61ea674cdab7`. Owner source files were not edited.

Seven independent methods passed through actual generated pytest subprocesses and disposable Git repositories. They cover numbered collision aliases, sequential partial repair with an omitted failing file, atomic refusal of conflicting alias/canonical repair blocks, identical alias repair as a positive control, a newly colliding repository path during repair, late directory or file collisions, and patch refusal when a path appears after a green run. Successful proposals were checked and applied with Git while preserving original repository bytes.

`REVIEW.json` and `independent-results.xml` are the original frozen receipts. Paths such as `source/testpilot/loop.py` in that receipt describe the isolated review layout. For replay after publication, use the repository root as the source directory and point pytest at the accompanying `test_independent_preservation.py`:

```sh
PYTHONPATH=. python -m pytest docs/evidence/ultra-20b27c2e-20261008/independent-runtime-integration/test_independent_preservation.py -q
```

Run from the TestPilot repository root with pytest available. The review test verifies the exact implementation SHA-256 before each case, so a later source version requires a new review rather than an inherited passing claim. The original observed environment was Linux, Python 3.12.14, pytest 9.1.1 and Git 2.51.1; the retained JUnit reports seven passes, zero failures, zero errors and zero skips.

Model responses were authored fixtures. No live provider request, native Windows filesystem result, hostile generated-code containment, or production adoption is claimed by these receipts.
