# Independent TestPilot match/case receiving review

Reviewer: `estate_coordination`, cohort `3dcb83a1`, 2026-10-08 UTC.
Decision: **accept the bounded match/case traversal candidate**.

The new traversal makes functions and methods defined in match case bodies
available to the existing changed-function selector. It preserves lexical
function attribution and class identity. The independently exercised native
TestPilot consumer generates an applicable patch for a previously omitted
method while retaining an existing test at the suggested output path.

## Exact source and executable

| Material | SHA-256 |
| --- | --- |
| Original `testpilot/diff.py` | `d1f22e3b594f9b8c657de6a69e4c44bb32c2a24819165dadb9e8a5a50d0dc5fc` |
| Candidate `testpilot/diff.py` | `59e5042a548900f234177a281df0b1d6468ce19be79e2f5e84dd205f35394f4e` |
| Current composed `testpilot/loop.py` | `dd79fbfbdcab00978b288835645c1b5adf37fec404ec0fa6da0ac41d45a79cbf` |
| Independent four-method review | `9e0732fdc2c297e432259748199f740bc34ecd7e3f1a2cd15ba65073623e4608` |

The reviewer independently copied the author's current receiving package into
two private directories. The five unmodified package modules are identical
between baseline and candidate; only `diff.py` differs. `source-manifest.json`
records all 12 copied files. Each execution receipt records the six imported
source hashes and verifies that they remained unchanged.

## Results

| Native execution | Result |
| --- | --- |
| Current-loop composition with original selector | 4 methods: 3 failures, 1 passing inherited-behavior control, zero errors |
| Current-loop composition with candidate selector | 4/4 pass normally |
| Same candidate with optimized Python | 4/4 pass |

These counts are independent of the author's 84-method receiving selection.
No broad suite, coverage improvement or provider-model quality claim follows
from the four-method review. Exact Python version and flags are in the receipts.

## What the separate review checks

1. A decorated method in a class defined inside a module-level match retains
   `Scale.times`, module `pkg.scale`, import name `Scale`, method flag,
   decorator-inclusive line span 5–11 and exact changed line 11.
2. Two case bodies defining the same public name produce two separate source
   spans and changed-line records. Undefined subject/guard names are never
   executed during inspection.
3. A match and local class inside a function remain attributed to the enclosing
   function, preserving the selector's existing lexical boundary.
4. A real Git diff changes the method inside the match-defined class. Actual
   `TestPilot.run`, `ScriptedModel`, the composed current loop and native
   pytest produce two new tests. One original sentinel test remains: the final
   native run reports three passed cases.

The consumer deliberately supplies an existing `tests/test_scale.py` and asks
the editor fixture to use that same filename. The current preservation behavior
renames the generated addition to `tests/test_scale_testpilot.py`. The patch
passes real `git apply --check`; original source and existing test bytes stay
unchanged, and generated tests are not applied to the original fixture.

With the original selector, the same actual consumer returns `no_changes`,
makes zero scripted model calls and produces no tests or patch. Its empty patch
fails `git apply --check` with exit 128. The candidate calls the two deterministic
scripted stages, selects `Scale.times` and returns `passed`.

## Replay and evidence

```bash
TESTPILOT_REVIEW_SOURCE=/absolute/candidate python3 -B independent_review.py
TESTPILOT_REVIEW_SOURCE=/absolute/candidate python3 -O -B independent_review.py
```

The source directory must contain the six pinned `testpilot/` modules. Set
`TESTPILOT_REVIEW_RECEIPT` to save a JSON receipt. Retain
`independent_review.py`, `source-manifest.json`, `run-summary.json`,
`files-manifest.json`, the baseline normal and candidate normal/optimized JSON
receipts, their raw stdout/stderr logs, and this note. The files manifest was
captured before this review note was added.

All repos, tests and model replies were authored isolated fixtures. The review
uses no provider request, account credential, estate job, service mutation or
shared source edit. It does not infer which conditional definition is active at
runtime: discovery is static, as with existing if/try/with traversal. The
candidate changes no Git-path decoding, source containment, sandbox timeout,
test-preservation or generation policy.
