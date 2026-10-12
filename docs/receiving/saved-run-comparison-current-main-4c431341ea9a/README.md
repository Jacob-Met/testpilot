# Saved-run comparison composed with main 52275f5

This receiving record qualifies the unchanged saved-run comparison on the newer
main runtime. It preserves the earlier source, reports, browser receipt and
delivered packet at their original immutable pins.

## Source composition

The two merge parents are:

- Current main observed on 2026-10-12:
  [`52275f50e672c145d8f69e90cf40948ab28a7d79`](https://github.com/Jacob-Met/testpilot/commit/52275f50e672c145d8f69e90cf40948ab28a7d79).
  Since common base `c32b5459657ec26aac9837b823b1bc326510873e`, this incorporates
  PR #77's retryable-response closure and PR #78's bounded optional-coverage
  detection.
- Published comparison and complete receiving evidence:
  [`96a71bf2c418f56d6262dc36be5de3500f8fcfee`](https://github.com/Jacob-Met/testpilot/commit/96a71bf2c418f56d6262dc36be5de3500f8fcfee).
  Its product-source parent is
  [`cd15c2db2e4cd6ff07f40f85103c30137f32ba5c`](https://github.com/Jacob-Met/testpilot/commit/cd15c2db2e4cd6ff07f40f85103c30137f32ba5c).

The merge completed without a conflict. Before adding this receiving record,
the composed tree was `947f89c5f160b4a22ba5a079439b19d9f9c7e741`.
`composition-source.json` records Git modes, object types and blob identities
for all 16 paths changed by newer main and all 51 paths changed by the published
comparison. The path sets are disjoint, and every recorded leaf matches its
respective parent. The other 1,497 common-base leaves are unchanged. This
includes preservation of main's `testpilot/model.py` and `testpilot/sandbox.py`,
their focused tests and receiving evidence. The comparison modules, CLI
addition, documentation, examples and prior receiving records are unchanged
from the published comparison parent.

## Focused runtime check

The only intervening behavior used by the native comparison fixtures is
optional-coverage detection. The current composition ran the existing real
producer/compare fixtures together with main's real-process coverage-probe
tests:

```sh
python -m pytest -q -p no:cacheprovider \
  tests/test_compare_native_coverage.py tests/test_coverage_probe.py
```

Result: **10 passed in 5.08 seconds** on Python 3.12.14, pytest 9.1.1 and
coverage.py 7.16.2. The complete combined output is in
`candidate-coverage-composition.log`; the exact command, environment versions,
timestamps, exit status and log digest are in
`candidate-coverage-composition.json`.

These cases cover actual pure-deletion and explicit-unchanged native reports,
measured zero coverage and absent coverage, byte-exact original JSON downloads,
the no-model/no-test compare route, and the newer probe's success, failure,
timeout, closed stdin, discarded output and interpreter-start error behavior.
No product implementation was altered for this composition.

## Existing acceptance and delivery

The prior [receiving record](../saved-run-comparison-current-4c431341ea9a/README.md)
contains the original failure witness, corrected 90-test gate and independent
native browser/download receipt. Those observations belong to their stated
source pins. The focused check above is the new observation on this composition.

The [delivered packet](../saved-run-comparison-current-4c431341ea9a/DELIVERY.md)
remains the same 38,520-byte ZIP with SHA256
`7e1790350109c2336076bdb72d968f295cfc394edb45431e550a09774c5c7c78`.
Its native example HTML and saved input reports are unchanged; this composition
does not create a second delivery or recast its synthetic examples as measured
quality improvement.

The earlier draft-PR creation attempt was rejected by GitHub's secondary
content-creation limit at 2026-10-12 21:33:39 UTC, request ID
`83F5:3DA636:1A057B6:559C6FA:6ACD5229`. No PR number was returned. A source
branch, commit or this local receiving record alone does not establish main
adoption. The unchanged CI workflow runs only on pushes to main and
`pull_request`; publication commits carry the standing skip markers.
