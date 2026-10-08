# Run timeout admission receiving

`testpilot run --timeout` now requires a positive finite number of seconds. Argument parsing rejects NaN, infinities, overflowing float text, zero and negative values before reading the diff, constructing a client, launching pytest or publishing reports. Fractional seconds, scientific notation and the existing 60-second default remain supported. The product edit is one `math` import, the private `_positive_timeout` converter, and the `run` argument type/help. Recheck and the sandbox are unchanged.

## Exact source and before/after evidence

Original main: `191cca4e416286a9e1fa4b5d5daf5fc30b936db6`. Qualified composition: `cec50d8df4499ba509615e179d82ef3861379bd2`, preserving PR42 raw Git acquisition. Final CLI SHA-256: `db5c92b169a40473371ed8e660bdc38133be6f167adbd2b8af24a966c4ba2320`; Git blob: `e81f31a9e89c78231cba0d9f69e92fe103db6ba0`.

- `baseline-pytest.log`: 9 failed, 5 passed; invalid limits reach the missing input instead of refusing at admission.
- `candidate-pytest.log`: 14 passed, including actual scripted generation and pytest with default and explicit positive timeouts.
- `before-receipt.json` / `after-receipt.json`, `baseline-driver.log` / `candidate-driver.log`, and `receive_cli.py`: actual CLI empty-diff controls establish that nine invalid limits previously replaced four retained synthetic output files; the candidate preserves their exact hashes. Positive controls retain ordinary no-changes reports.
- `independent/original/`: independent receiver and original source/patch/receipts, 11 passed and 9 failed before; the candidate passes 20 checks. These include distinct stdin and input/output preservation controls, with zero model requests.
- `independent/current-main/`: the independently reconstructed current composition passes the same 20 checks. Receipt SHA-256: `0b1846f41ec725787e7cae573fe6eaf2ae13aa2469188c4e5689fc6ca7629ccd`.

## Incomplete affected gate and bounded continuation

The original seven-module run collected 51 tests and reached 35 pass progress dots before its 160-second outer limit. `composed-incomplete-gate.json` and the unchanged raw log retain **INCOMPLETE**, with no pytest return code. This is not a completed gate or a product failure. Collection order is retained in `composed-collection.log`.

The remaining 16 nodeids were then selected explicitly, starting at `TargetPreviewTests::test_help_and_source_options_do_not_accept_generation_options`. `composed-remaining-pytest.log` records **15 passed, 1 skipped, 13 subtests passed** in 9.44 seconds; the driver completed in 9.8 seconds with exit 0 and unchanged source. The skip is the pre-existing optional-coverage boundary because this native interpreter has no `coverage` module. No whole gate or full suite rerun is claimed. `final-receiving.json` records the precise disposition and parent-preservation count.

## Reproduction and integration

Run `python3 -B -m pytest -q tests/test_cli_timeout.py` in the exact candidate. The actual CLI driver accepts a source checkout and a new evidence destination: `python3 docs/receiving/cli-timeout-f5c43297f890/receive_cli.py SOURCE NEW_DESTINATION`. Independent receiver commands and source bindings are recorded in their receipts. All receiving uses authored private fixtures and already installed tooling.

`source.patch` contains only the two parent-file edits. Apply those edits over the actual receiving parent; do not replace a newer whole CLI or README. The documentation composition initially omitted PR42 guidance; it was restored from the exact composition parent before this packet. `readme-composition-proof.json` verifies that removing only the timeout paragraph reproduces the complete cec50d8 README bytes. Existing claim/setup and incomplete-run records remain historical rather than rewritten. Root owns serialized publication and actual hosted CI/merge qualification. Native source qualification does not establish a deployment, Windows behavior, model quality or a universal guarantee for tiny positive deadlines.
