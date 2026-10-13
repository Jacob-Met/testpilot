# Resolved test-path source qualification

Reviewed source: [`e7853b05`](https://github.com/Jacob-Met/testpilot/commit/e7853b0545b9938d1df14ba81706d1f5ad03f8ab)
(parent `478f68adf01658a94a3ede22526da00f580785bd`).
Tracking: [issue 93](https://github.com/Jacob-Met/testpilot/issues/93).

Automatic selection now excludes a diff alias whose confined resolved
destination is test source. The two-line guard retains lexical exclusions,
confinement errors, explicit test inclusion and ordinary source aliases.
The source increment changes only `testpilot/diff.py`, the source-boundary
guide and the new 13-case regression file.

## Qualification

| Course | Original | Candidate |
| --- | --- | --- |
| New authored regressions | 4 pass / 9 fail | 13 pass, within focused course |
| Frozen independent receiver | 17 pass / 9 fail | 26 pass / 0 fail |
| Maintained focused course | Not run as a full original course | 77 pass / 1 fail |
| Maintained full course | Not rerun in full | 648 pass / 7 fail / 1 skip; 40 passing subtests |
| Seven failing maintained tests | All 7 fail on clean original | Same 7 fail in full course |

The full maintained suite remains failed. Three unchanged fixtures raise Mac
errno 92 when creating raw-byte filenames before product selection. Four
collection/recheck assertions also reproduce on the original; no new cause
is claimed. Existing tests and skip rules were not changed. All six maintained
files containing those failures were independently verified unchanged.

The [bounded source review](independent-source-review.json) and
[saved qualification review](independent-saved-qualification-review.json)
record independent acceptance and its limits. [RECEIVING.json](RECEIVING.json)
contains exact sources, commands, runtime versions, log pins and separate
pytest/observer exit results.

The later [published-source receiving record](independent-published-source-receiving.json)
independently verifies the actual GitHub commit, tree, parent and complete
three-file bytes. It is kept outside the already sealed capsule. The source
patch also passes `git apply --check` on the clean exact original.

## Exact downloadable handoff

[TestPilot-resolved-test-paths-e7853b05-20261013.zip](TestPilot-resolved-test-paths-e7853b05-20261013.zip)

- Bytes: 42761
- SHA256: `86e565287dfdefc4bfebc809544aae1d7a8545af8860c3358006cb120365328e`
- Members: 19; byte manifest included

The capsule includes the three exact source files, a patch against the pinned
parent, all six unchanged independent artifacts, the original API/CLI witness,
all four authored original/candidate test logs and the detached-baseline
record. It is a change and qualification capsule, with the complete project
available from the source commit above.

Publication uses an isolated non-main branch. No PR, main integration,
workflow change, provider/installed adoption, Windows qualification or Drive
receiving is claimed. Detached explanation/indexing/other source owners retain
their existing scopes.
