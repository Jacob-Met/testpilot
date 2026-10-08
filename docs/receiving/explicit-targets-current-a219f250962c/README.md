# Explicit targets on the current output-staging source

This small companion records PR #38's source reconciliation onto canonical
`7f44c4f134f4d56d37dd14c7c2d2aaa3c8c8749e`, after the first publication
`e971f4490e9a6c8c23d9e645e47232632cd015e3`. The branch update retains both
parents in that order and does not replace earlier history.

## Exact composition

Six of the eight author source, test and documentation files remain byte-identical
to independently accepted native `00b63c8e03cc515160da1202331224167d12d253`.
The two shared files compose as follows:

- `testpilot/loop.py` retains the current PR #34 imports and the complete
  2,001-byte `write_outputs` suffix verbatim. Reversing only those owner additions
  recovers the accepted explicit-target loop bytes exactly.
- `README.md` retains both the accepted explicit-target section and the current
  owner's complete report-saving section. Removing either exact addition recovers
  the other source version.

Current source outside the eight author paths remains the current parent's source,
including the module-identity correction, raw loader, sandbox, model/client,
recheck, fence/patch, allocation and coverage code. The full-tree construction
preserves all 1,059 unrelated current-parent leaves; `source-map.json` binds the
two source versions and all eight resulting author file hashes.

## Preserved receiving and current limits

The original 63-file, 437,821-byte receiving packet remains byte-for-byte intact at
[`../explicit-targets-a219f250962c/`](../explicit-targets-a219f250962c/).
Its manifest SHA-256 remains
`6dece6ae88d4822d7b3a47a4709ab224dcf7eca70b78d945660b4283dea65937`.
It retains the exact scoped history, original no-changes/unsupported-option
witnesses, all authored and independent results, actual model messages, generated
patch, and the paired e228/631 native baseline limitations.

Those native results qualify the frozen 00b/631 source. This current composition
has separate exact source checks and Python AST parsing; hosted full-tree CI and
root independent public receiving qualify the combined current version. This
document does not claim a new native execution of the current composition or
live-model generation quality.

The final composition was assembled in memory after the native free-space gate
held additional writes. Existing native source and separate native packets remain
preserved. Canonical GitHub contains these final bytes; no new unified native
packet or archive is claimed.
