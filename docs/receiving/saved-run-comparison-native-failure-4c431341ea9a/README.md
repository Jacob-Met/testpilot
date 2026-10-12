# Keep native runner failures reviewable

The saved-report comparison accepts a native timeout's explicit null return
code. It retains the recorded failure, timeout summary and unavailable execution
counts. The return-code key remains required; non-null values retain the same
exact-integer type and magnitude limits.

## Actual failure and correction

The new `tests/test_compare_native_runner_failure.py` creates two real native
baseline failures. One pytest process reaches a collection marker and then
exceeds the two-second deadline. The other uses a temporary Python environment
created without pytest, pip or system site packages. Both preserve the current
producer's failed result, original diagnostics, empty model-call ledger and
empty generated patch.

On the received comparison without this correction, the timeout report is
refused by the CLI with exit 2:

```text
report.final.returncode: expected an integer from -9007199254740991 through 9007199254740991
```

The original result was **1 failed, 1 passed in 2.14 seconds**. The missing-pytest
control, which records integer return code 1, already passed. The complete raw
failure output, command, timestamps and output hash are retained in
`original-native-failure.log` and `original-native-failure.json`.

The implementation changes only `_result` in `testpilot/compare.py`: distinguish
an absent key from an explicitly recorded null, then apply the existing integer
check to any non-null value. The HTML renderer is unchanged. This accepts an
existing native representation; it does not substitute a zero exit code or
infer successful execution from missing data.

The corrected focused command was:

```sh
python -m pytest -q -p no:cacheprovider \
  tests/test_compare.py tests/test_compare_cli.py \
  tests/test_compare_native_coverage.py tests/test_compare_native_runner_failure.py
```

Result: **45 passed in 7.66 seconds**, using Python 3.12.14, pytest 9.1.1 and
coverage.py 7.16.2. `candidate-native-failure.log` contains its complete combined
output; `candidate-native-failure.json` records the exact command, versions,
timestamps and output hash. The cases retain strict malformed-input admission,
the no-model/no-test comparison route, byte-exact BOM/CRLF original downloads,
unavailable complete-suite counts, the earlier null changed-line coverage
semantics and measured zero coverage. This is a focused gate, not a new claim
about the entire repository suite.

## Source composition and independent review

This descendant combines the previously qualified comparison composition
[`f8d7297ceba9cb03cfe8f2ca59a4b75b8870bc2e`](https://github.com/Jacob-Met/testpilot/commit/f8d7297ceba9cb03cfe8f2ca59a4b75b8870bc2e)
with main
[`86617fc90becf79b20d9cf5212b848bff8227147`](https://github.com/Jacob-Met/testpilot/commit/86617fc90becf79b20d9cf5212b848bff8227147),
which adds PR #80's early refusal when the baseline runner produces no complete
report. Its three changed paths retain their exact modes and blobs:
`testpilot/loop.py`, `tests/test_baseline_runner_admission.py`, and
`docs/BASELINE_RUNNER_ADMISSION.md`.

The local qualified parent `79522b644a5530a42c25654c486483b86238c504` and remote
parent f8d7297c share tree `7f2ed85c1a250bd860dbcecb56cf0aae8f28795c`.
`source-composition.json` records the added main leaves, unchanged parent leaves,
and qualified product-file identities. A shell fetch's network-approval wait
was cancelled after the new commit object arrived; the three missing text
blobs were read through the authorized GitHub connector and their Git SHA-1
identities were verified before the local merge.

The independent `/root/shared_delivery` reviewer verified exact preservation
of those three main files and the other 1,568 parent leaves before this narrow
fix. The reviewer also checked the null/key distinction, unchanged integer
admission, unchanged renderer, real-process tests and matching documentation.
`peer-source-review.json` records that source review. It involved no additional
test runs, browser observations or external delivery changes.

The shared disk filled while writing this record. Sealing therefore used a new
task-owned temporary checkout. All 1,571 tracked working files, the new test and
the complete native-failure evidence were compared byte for byte to the tested
checkout before writing this record. The tested source and prior published
branches were preserved. `source-composition.json` records this custody step.

## Open the native example

Open [native-example/comparison.html](native-example/comparison.html) directly
in a browser. Before is the actual timed-out baseline from the passing gate;
After is the actual missing-pytest baseline. These are synthetic runner-failure
examples with different setups, not a before/after quality-improvement claim.

The separate compare CLI process wrote the 16,076-byte page with exit 0, retained
both diagnostic messages, and embedded the exact two saved input byte streams:

| File | Bytes | SHA256 |
|---|---:|---|
| `before-timeout.json` | 1,190 | `ec995a7a284974ec4246eb28de80bee8ebe99d1d9c926949224bc583880c5dad` |
| `after-missing-pytest.json` | 1,278 | `1e762a8005e64804fe21743f419d1103e66862ad4993c898f7043e41dda90e1d` |
| `comparison.html` | 16,076 | `7d425770751eb5932e62bc63564cb1500f9d6f46bc37ece460f15e0de6632fa5` |

`native-example/receipt.json` records the exact process, native input origins,
source hashes, output hash and original-download verification. No new browser
observation is claimed for this new example. The earlier independently received
HTML renderer and its [delivered coverage example](../saved-run-comparison-current-4c431341ea9a/DELIVERY.md)
remain byte-identical and retain their original source and receiving pins.
