# Installed TestPilot scripted review kit

This contribution receives the unchanged package and original calc_clamp example
from accepted source d2596c1a4be11072344c4ea98752cce789865ec4, tree
3b6d270f655310fa2f98cab9bccffca23ec146cf. It changes no TestPilot product code,
packaging configuration, workflow, example or held owner contribution.

The ordinary wheel was built without dependency downloads, installed into a new
isolated receiving environment, and used outside source. Help and target preview
exit 0. The actual scripted run has the expected exit 1 / suspected_code_bug:
three failing and three passing tests, including four generated cases. It writes
all four report/patch files while preserving every original example input.
This keeps a deliberately broken implementation visible instead of weakening
its tests. It is a deterministic pipeline example, not a live-model quality claim.

See START_HERE.md for portable installation and sample commands. The archived
cloud receiver retains its original absolute task paths and records that one
receiving course; it is not the portable user entrypoint.

## Identity and scope

- Exact accepted source: https://github.com/Jacob-Met/testpilot/tree/d2596c1a4be11072344c4ea98752cce789865ec4
- Existing source/receiving issue: https://github.com/Jacob-Met/testpilot/issues/105
- Wheel: 75,206 bytes; SHA256 c471d961e1b26051209b2d8bdcf0629b1f0185b25ae6c0d0d733bacca344d246.
- Corrected v2 kit: 107,866 bytes; SHA256 8b3c856751ae9bd24b74474b68624e38e97d9157429aafc6c9d671676be00a4d.
- V2 has 31 members, 30 manifest payloads; all member bytes and CRCs verified.
- All 25 source/metadata/sample files match their published Git blobs; all 14
  installed package modules remain byte-exact after the actual consumer run.
- The cloud interpreter is Python 3.12.14. Its runtime environment reads existing
  pytest 9.1.1 from a separate read-only dependency provider. Builder tools are
  setuptools 84.0.0 and wheel 0.48.0. No dependencies were downloaded.

Independent preflight caught the v1 manifest's mislabeled source-tree value:
it contained the commit ID. V2 corrects only that field and the enclosing
manifest hash. All other 29 members, including wheel, sample, user guide and
actual receiving outputs, remain identical. V1 and correction identities are
retained separately; source, build and consumer behavior did not change.

The raw records distinguish actual native test outcomes from process wrapper
success. In particular, the scripted process's expected exit 1 is retained as
exit 1. The report has real failing cases and is not described as a passing patch.
This bounded qualification does not rerun the complete maintained suite, prove
browser visual behavior, call a live model/provider or adopt an installed estate
application. Native Linux receiving is completed and recorded in native/README.md.

## Delivered artifacts and independent review

- [Read first](https://drive.google.com/file/d/1t7K9EJj6GARw6bw-8OvDl3gpdh6sXuLo/view)
- [Frozen v2 installable kit](https://drive.google.com/file/d/1B2lGm_l5bApgUDNqc4SL9B1szHETfIge/view)
- [Complete native receiving companion](https://drive.google.com/file/d/1CKWSbmSV4HTzybO8MzQmmAYSJPeQcu_g/view)

The native companion is 58,471 bytes, SHA256
88884d68deb8e0315dd025c5649883a936d00114c0ddd32d553273f2da0f24aa.
It preserves both native export attempts, the exact final receipt, raw routed
custody and independent custody review. The isolated ThinkPad installation used
Python 3.14.4 with existing pytest 9.0.2; all seven receiving checks pass.
See [the native guide](native/README.md) for the actual process exits and limits.

independent-cloud-review.json records a second worker's source, guide, archive
and report inspection. The archived cloud receiver checks installed module
bytes before commands; the independent reviewer subsequently rehashed all 14
installed modules and verified that they still match the wheel and source.
Neither independent review reran the actual consumer. The complete cloud and
native records retain their own runtimes and do not imply qualification of a
later product commit merely because these evidence files are integrated later.

All three delivered files were downloaded again and matched the local bytes;
the two ZIPs passed every payload size/hash and archive CRC check. Exact
readback receipts are included here. No existing source, test, sample, packaging
metadata or workflow is changed by this receiving contribution.
