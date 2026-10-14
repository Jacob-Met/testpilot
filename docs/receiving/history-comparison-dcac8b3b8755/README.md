# Saved-run discovery to comparison walkthrough

This documentation/example increment connects the existing commands without
changing runtime source. Use the [runnable example](../../../examples/saved-review/README.md)
to discover two fictional generation reports, assign Before/After roles and
create a portable comparison.

## Source and actual results

The source is main `83c43077b7fcb168de43e15274f6e8f1f6b37d3c`, tree
`e330681460baa0deaf38fc5484ab9475d79c5da7`. The actual 16-module CLI closure is
bound by the earlier [source record](../compare-case-index-dcac8b3b8755/SOURCE.json).
The walkthrough verified each body against that closure before execution.

The first history command used the two exact fictional JSON downloads from
the accepted comparison-index artifact. History exited 1 and listed both as
`invalid_report`; its [raw receipt](original-trial/receiving.json) and
[actual stdout](original-trial/history.stdout.json) are preserved. All source,
input and witness inventories remained exact. This was an incompatible fixture
trial, not a passing discovery or an established product defect.

Source inspection found that history requires `final.coverage`; native
`SandboxResult.to_dict()` includes it through dataclass serialization. The
comparison fixtures omitted it, which comparison admits. The new example
derivatives add `final.coverage:null` and reserialize JSON. The executed driver
proves that removing the added field restores the same parsed original value.
It records both byte identities and never edits the accepted originals.

The [actual workflow receipt](workflow/receiving.json) records CPython 3.12.14,
one ordinary history command and one ordinary compare command, both exit 0.
All 15 checks passed: two path/hash-matched generation rows, complete discovery,
six correctly ordered unique occurrence targets and two embedded original
downloads byte-equal to the derivative input files. Four source/input/original/
witness before-after inventories remained exact. The raw receipt is Git blob
`21a9580450b4a1876eab9f8a455ed583413ec87f`, SHA-256
`af90ada3288dbb5faabc78c80bf410c3a4c6de2c79974794cd57bc783319a619`.

These are CLI and generated-HTML structural checks, not 15 browser tests.
No model, retained test body, saved patch or external service was executed.
The accepted comparison-index browser qualification remains separate. The
historical receiving drivers reference their original staged paths; the example
README supplies the portable commands users should run.

`MANIFEST.json` lists the exact example and evidence file identities, excluding
itself and the two maintained guides. The source tree and normal PR review bind
the guide changes. Existing source and accepted receiving records stay intact.
