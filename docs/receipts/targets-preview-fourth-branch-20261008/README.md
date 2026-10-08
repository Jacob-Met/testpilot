# TestPilot target preview: source and receiving packet

This contribution exposes the existing native diff selector through
`python -m testpilot targets --repo PROJECT (--diff FILE | --git-base REF) [--json]`.
The human view lists quoted locations; JSON includes the complete native function
records and source. A caller can inspect selection before requesting generation.

The preview constructs no model client, invokes no pytest and writes no generation
report or patch. The current `run` implementation, interpreter selection and
native Git acquisition behavior are preserved. Preview is not a Git configuration
sandbox or a reservation of the bytes used by a later generation.

## Accepted source

Only `testpilot/__main__.py`, new `tests/test_cli_targets.py`, and new
`docs/targets-preview.md` change outside this unique receipt directory. The CLI is
blob `fc455a5b4866fd27503585a50903a80ff179513e`, unchanged from author freeze
`9c2c3ef951cc0a0c063c70179e39e86797ee129b`. The original source baseline is commit
`9f01fcb6de085850eca00db746380795eb548d62`.

Publication is composed onto complete current main
`d7c28b0ad261e78d681f40e355447dffa4d435ed`. The original CLI beforeimage remains
exact. Merged PR #14 added generated-test collection/result behavior and PR #15
added Python source encoding support after that baseline; their current loop,
sandbox, decoder and helper are all preserved byte-for-byte. The incoming changes
use those native implementations without replacing them. The established CI
workflow is also preserved.

## Qualification

The immutable author packet records eight focused methods passing normally and
under optimized Python, each with 15 actual module CLI children and one direct
main tripwire. Seven baseline methods leave nine assertions and one error
unsatisfied; the existing native empty-diff run control passes. The final optimized
receipt propagates `-O` to its children. The earlier optimized-parent/normal-child
receipt and initial fixture notes remain as historical evidence.

The separate original receiver passes 34 conditions across five candidate CLI
cases, paired with five baseline children (11 unsatisfied baseline conditions).
It uses a real Git diff containing a pure deletion in an outer/nested function,
a decorated async method under a conditional class, and a newline/Unicode path.
JSON equals the native selector, human rows are quoted, preview avoids generation
and project imports, and a later syntax error produces no partial result. The
existing run parser and dispatch preserve all explicit options through declared
factory/runner/writer doubles. The author suite was not rerun by the reviewer.

The current-source composition repeats that same receiver with only its three
changed dependency pins rebound: all 34 conditions pass, with 11 baseline failures.
A separate actual CLI preview of a BOM-encoded Python file passes seven conditions
through the already-merged native decoder. Neither the decoder owner's suite nor
the generated-collection owner's suite is repeated here. All eight current package
and configuration blobs are pinned in `composition/current-package-pins.json`.
Hosted CI and final merge readback are separate publication results, not implied
by these local receipts.

## Packet layout and replay

`author/` preserves the original author README, source pins, portable qualifier,
full three-file patch, before/after outputs and fixture history. Its README and
`verify_preservation.py` describe the historical adjacent `baseline/` and
`candidate/` source slices. They are retained verbatim and do not run unchanged
from an ordinary published checkout; this packet does not duplicate those source
snapshots. The portable author qualifier accepts explicit source and test paths:

```sh
python -O -B author/evidence/qualify_targets.py --source /path/to/candidate --test /path/to/candidate/tests/test_cli_targets.py --out /path/to/new-author-results.json
```

`independent/` retains the original exact receiver and results. Its script checks
the original baseline/candidate and six support pins before constructing disposable
Git fixtures. `composition/` retains the same receiver rebound to the current
native support, its unchanged-logic proof, and the BOM-interface receiver:

```sh
python -B composition/receive_targets_current.py --baseline /path/to/current-baseline --candidate /path/to/current-candidate --out /path/to/new-current-results.json
python -B composition/receive_bom_preview.py --candidate /path/to/current-candidate --receiver composition/receive_targets_current.py --out /path/to/new-bom-results.json
```

The source roots are explicit inputs. For the composition receiver, the baseline
is the publication-base package; the candidate combines that exact package with
the accepted CLI, new test and documentation. The original receiver instead uses
the earlier original baseline package. All source identities and content hashes
are recorded; `manifest.json` pins the production files and this complete packet,
apart from itself.

## Limits and ownership

Receiving uses disposable local Git/Python processes. No provider request, model
quality evaluation, live host/account/service, installation or activation occurred.
The independent run-dispatch controls use declared downstream doubles; the author
retains a separate native empty-diff ScriptedModel/report control. No native
Windows or full local repository suite result is claimed. Git acquisition retains
Git's configured behavior, and source changes after a preview can change later
generation. Scope is coordinated in repository issue #2; its source-decoding,
model-timeout, collection, sandbox and CI owners retain their implementations.
