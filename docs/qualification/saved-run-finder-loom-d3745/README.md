# Find retained TestPilot reports

`python -B -m testpilot history --root DIR` finds saved generation and recheck
records beneath an explicit directory. It returns literal relative paths, the
recorded status, useful target/test labels and the SHA-256 of each original JSON
body. It does not run a model, generated tests, a recheck or a recorded path.

Start with the [maintained usage guide](../../HISTORY.md). For example, from
the complete checkout containing this feature:

```sh
python -B -m testpilot history --root eval/results --json
python -B -m testpilot history --root /absolute/path/to/saved-results --query clamp --kind generation
```

The default depth is one directory below the explicit root. `--max-depth 0`
examines only root-level candidates. Query matching is literal and casefolded;
status filters are ORed, with query/kind filters applied together. Discovery
and validation happen before filtering, so a malformed neighbor still produces
a partial result even when it would not match the chosen filter. Exit 0 means
complete discovery, exit 1 means a printed partial result, and exit 2 means an
option/root/output failure. A historical failing status is still a successfully
found record. Check `complete`, `problems` and the exact reported path.

The finder is bounded to 1,000 candidate files, 20,000 scanned entries, 16 MiB
per file and 64 MiB of body reads. Internal symlinks are skipped; nonregular
candidate files are reported without reading their body. The root is resolved
explicitly. These bounds and before/after observations are not a concurrent
filesystem snapshot or a guarantee against hostile mutation.

## Source and qualification

This is the five-path continuation of existing [issue 39](https://github.com/Jacob-Met/testpilot/issues/39),
preserving its original source-integration credit. The original base is
`f9ba2d2260f7aa93b3958661aa178ad418df9af6`. Only the new history module, focused
test file and usage guide, additive CLI dispatch/parser/import, and a small
README section are production changes. Other modules and the inherited workflow
remain unchanged. `source-binding-v1.json` binds the exact five final bodies,
the original 21-file projection and complete original parent tree.

The [author history](author/README.md) retains the original unknown-command
refusal, public contract and both clarifications, first 21-method normal and
six-method optimized courses, five unchanged inherited help-command pairs,
and the exact V1-to-V2 unbuffered descriptor correction. V2's separate four
focused controls passed; the original V1 source and receipts stay unchanged.

The [independent receiver](independent-root/README.md) froze its own 34 literal
CLI expectations before candidate exposure. One course passed all 34 at the
real published limits, preserving every selected source, control and input
namespace. Its original 7,352,312-byte case specification is stored as a
deterministic gzip with exact decompression binding; its generator and all
34 expected stdout files and 68 actual stdout/stderr streams are preserved.
The oversized generated seed bodies are intentionally reconstructed by that
unchanged generator, not replaced with smaller boundary tests.

Forge independently reviewed the full final five-file source and exact additive
diffs; its source review is retained in the independent descriptor. The two
earlier public-contract reviews remain separate peer support. No whole-suite,
native installation, historical business-outcome validation or user acceptance
is implied by these scoped results.

Both original publication descriptors are preserved byte-for-byte. The maintained
publication layout gate admits five source rows, explicit support rows and the
unchanged independent descriptor; no workflow or unrelated path is selected.
Historical absolute paths, timings and unpublished-at-execution metadata remain
unaltered. Existing older wheels and installed copies do not gain this command
until separately updated from the published source.
