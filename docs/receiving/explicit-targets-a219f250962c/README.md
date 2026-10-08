# Explicit named targets — source receiving packet

Repository: https://github.com/Jacob-Met/testpilot
Claim: https://github.com/Jacob-Met/testpilot/issues/30
Comparison coordination: https://github.com/Jacob-Met/testpilot/issues/26#issuecomment-6061973659

This packet preserves a native developer capability: repeated --target path.py::qualname
on targets and run selects exactly the requested current functions. It carries the
exact loaded diff and selected function source through planning, generation and repair.
Default automatic selection and output remain unchanged. Selection is deliberate;
no dependency completeness or live-model generation quality is claimed.

## Exact source

Current canonical receiving base: 63174afd8e63a0ea562cf188b7d971522f017a30,
tree cea947d9aeb2253466593044889a1bb548f8b7c4.
Frozen scoped source: 00b63c8e03cc515160da1202331224167d12d253,
tree d1ba76e3872a0e843821b799f8accb69aa32416d.
Scoped baseline: 33a10cd5b756b8ade8768bd6f8da75f55da369c3.

The scoped materialization contains 27 files, not the complete canonical repository.
Its complete local source history is preserved in source/source-history.bundle.
Do not merge this snapshot ancestry into the canonical repository.

source/explicit-targets.patch contains only the eight claimed source/test/doc
deltas over the current receiving base. source/receiving-manifest.json lists every
required preimage and postimage. Ordinary git apply --index --check followed by
git apply --index in an isolated exact baseline received all 27 scoped leaves
byte-for-byte, preserving all 19 untouched baseline leaves. Keep all other
canonical repository files when composing the source branch. If current main has
changed these preimages, reconcile the exact additive seams and record a new pin.

The saved-test recheck implementation, sandbox exact_files option, documents and
tests are the owner's exact 631 source. All three recheck CLI additions are preserved.
The raw diff loader, function discovery, generated-file allocation, fence/patch
functions, execution and coverage contracts remain unchanged.

## Authored native qualification

Existing Python3.12.8 / pytest9.1.1 / coverage7.16.2 was used read-only with
PYTHONDONTWRITEBYTECODE=1 and PYTEST_DISABLE_PLUGIN_AUTOLOAD=1. No installation
was performed. All 12 new explicit-target tests pass in both source compositions,
including real ScriptedModel generation plus repair and exact outgoing prompt
context assertions.

The original e228 composition is retained at fc24a55d2c5e2d94478072e8e6736bf44bab81a6.
Its selected regression run passed 126 tests and 18 subtests. Two unchanged
non-UTF-8 filename fixtures failed at Path.write_bytes with macOS errno92 before
TestPilot ran. The identical two failures were reproduced against untouched e228
source. Raw results are retained; the fixtures were not changed.

The current631 composition's five-module control passed 58 tests and 18 subtests,
with one existing skip. One unchanged saved-test recheck test expected one total
passing case and observed two; its retained generated pass and failing configured
case otherwise matched. The exact same failure was reproduced in untouched631
source. This is an inherited native receiving limitation, not a green canonical
suite claim and not a recheck repair in this contribution.

checks/ retains both original runs and their bounded paired baseline controls.
baseline-assessment/ retains the original real no_changes/unsupported-option CLI
witnesses and all eight exact e228 source modules. No known test failures have been
removed or silently reclassified as passes.

## Independent receiving

Independent root source and native receiving ACCEPT the exact frozen 00b source.
All six groups pass on an existing Python3.13.7 / pytest9.1.1 / coverage7.16.2
environment. The receiver records 23 actual CLI/Git/pytest commands, three actual
ScriptedModel calls including repair with exact diff and selected source in each
message, ten refused selections before calls/output, Unicode/Latin-1 read-only
selection, exact default JSON parity, and a patch that applies and runs three tests.
The unchanged 21-file independent packet (137,606 bytes) is retained in independent/,
including all original messages, outputs, receiver source, source hashes and ACCEPT.
Its SHA256SUMS.json is 17d33526a6b44439e691f9b5cc503d172c15be86a7d83e90867a1b209c8ff6b2.

## Canonical publication mapping

Fresh public parent: f3b2135cad31852b599350564fe76dd160a6a522,
tree d0107a6f8b3b8cc00dadebc5f794060f275f3f5b. All eight author-path preimages
still match the received 631 baseline. Publish the eight accepted source leaves and
this unique receiving directory on that full parent tree; preserve every other
parent leaf. The actual public commit/tree and hosted CI remain separately recorded.

The parent added its own PR32 module_name condition correction in untouched diff.py,
retaining the lib package prefix. Exact source comparison verifies that one condition
is the only diff.py change from 631. This contribution continues to call the existing
native functions_touching/module_name implementation and preserves that current owner
source. source/publication-mapping.json records this distinction. The native receiving
claim stays pinned to 631; complete combined-tree hosted CI is a separate qualification.

The source-history bundle preserves scoped native history for source custody.
Canonical publication uses the full current parent and does not merge snapshot ancestry.
No service, resident worker, goal, database or live-model activation is implied.

Native final assembly was held by the declared free-space floor. Existing native draft and independent packets remain preserved separately. These final receiving bytes are published directly through the canonical GitHub source tree; no finalized native archive or unified native custody is claimed.
