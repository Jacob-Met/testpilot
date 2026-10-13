# Received TestPilot composition

This consumer joins three independently reviewed increments with main
`d2596c1a4be11072344c4ea98752cce789865ec4`:

- Bounded POSIX native output and portable interruption receiving: `6e75f9d0eda87ed2f01bed211e29b48d25bd0b4b`.
- Copied-project pytest configuration boundary: `7776adbe74d8740bac7f4d2669d6619f80b2a5e2`.
- Optional live progress and absent/failed stderr handling: `5dfb74c55aac430691fbf7847d5e3d8a10ac74b3`.

The newer main comparison-console branch is preserved. The only composition
within an existing newer carrier applies the three published progress CLI spans:
import, run flag and factory expression. The remaining feature source and tests
are the exact reviewed blobs. No model, loop, provider, dependency or workflow
logic is newly changed by the composition.

## Actual consumer

From the complete composed source, with Python 3.12, pytest and Git available:

```sh
python -B docs/receiving/composed-toolkit-7cb7e049e2c0/receive_composed_testpilot.py \
  --source . --out /path/to/new-receiving-directory
```

The receiver requires an absent output directory outside the source checkout. It
creates only its own synthetic project, fixed model replies and receiving files.
The command generates tests, makes one real repair, applies the saved patch to a
separate adoption copy and rechecks the exact saved tests without model calls.
It does not contact a provider or change the supplied source checkout.

The fixture's caller ancestor config selects only `selected/`. A separate legacy
test must still run in TestPilot's copied project. Each selected test writes
16 MiB to exercise continuous output draining; the final diagnostic must remain
in the saved 3,000-character output tail. Live progress appears on stderr. The
successful final and recheck runs have three passing cases, including the legacy
case and one retained generated case. Original and adopted pre-existing files
remain unchanged.

The published progress-only source reports two passing cases and omits the legacy
case under the same configuration trap. `baseline-control.json` records that
negative control. `author-consumer.json` records the complete composed workflow.
The initial author receiver used a filesystem spelling for native JUnit nodeids;
after correcting its expected classname spelling, the complete workflow was
received in a new directory. No production change was needed for that receiver
correction.

Independent receiving adds a stronger failing-test control: the separate progress
branch reports two passes while omitting an intentionally failing legacy test;
the joined source reports two passes and that failure. With the legacy fixture
passing, joined quiet and progress modes produce the same three passes, saved
patch and accounting after one repair. Every run writes 16 MiB through the actual
native pipe, and its final diagnostic remains in the bounded saved tail. A file
challenge proves the baseline is still held when the progress notice arrives.
Source and input hashes remain unchanged. `independent-consumer.json` preserves
these four cases; `composition-review.json` verifies the newer CLI equals its
exact main source plus only the three accepted progress spans. The independent
receiver is `receive_testpilot_toolkit.py`; use its `--help` for selected source
and output paths. Adoption/recheck are the complementary author receiving above.

## Maintained checks

The six selected maintained modules cover progress/API/actual CLI, native pytest
configuration, bounded output, portable interruption and the newly inherited
comparison-console behavior: 62 passed in 10.45 seconds. The initial portable
test subset omitted `test_compare.py`, which supplies a fixture to the comparison
console tests. That exact parent dependency is included; `setup-note.json`
preserves the initial collection outcome and correction.

This is local Linux/Python 3.12 receiving with native pytest 9.1.1. Separate
minimum-version configuration evidence remains with the original #91 increment.
These results do not assert a Windows run, installed-estate deployment, live
provider execution, main integration or future-version behavior. Source
publication is through a separately verified inert feature branch under the
current GitHub Actions prohibition.
