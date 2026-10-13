# TestPilot receives a real CaptureSuite EMG regression

This example connects the two received products through their public Python and CLI interfaces. TestPilot generates and retains two fixed-response tests, then its `regression` command runs those exact tests against the original and corrected CaptureSuite Python source. The recorded-disconnect test fails before and passes after. The no-gap control passes both.

## Replay the retained comparison

Use Python 3.12 and Git, the complete [received TestPilot toolkit](https://drive.google.com/file/d/1xmOx88ADOlw0-lVO377Gq-njsW_UANZi/view), and a prepared CaptureSuite analysis interpreter with its repository dependencies and pytest. The source packages are supplied by this packet; the selected interpreter supplies third-party dependencies. No provider account or live model request is needed.

Extract this packet, then run:

```sh
python -B replay_capture_emg_regression.py \
  --toolkit /absolute/path/to/toolkit \
  --python /absolute/path/to/capturesuite-python \
  --out /absolute/path/to/new-emg-regression
```

The output directory must not exist. The replay verifies all 16 TestPilot module hashes against the delivered toolkit, clones the included local Git bundle into the new directory, checks all 80 Python source files in both snapshots, and invokes the actual TestPilot regression CLI. Open the resulting `regression/regression.md` or `regression/regression.json`. The replay ends with an `ACCEPT` receipt and zero regression model calls. It preserves the supplied packet and the cloned worktree.

The standalone replay was actually received from this bundle in a fresh clone. Its complete receipt and result are in `fresh-replay/`. The original generation result, readable HTML, saved test patch and progress transcript remain in `generated/` and the top-level logs.

## What the test observes

The input has four EMG samples at 0, 25, 125 and 150 ms, with values +1, +1, -1 and -1. A recorded disconnect covers 50–100 ms, strictly between the two constant runs. All four samples remain valid. A feature extractor must not invent waveform length or a zero crossing across that unavailable interval.

| Retained test | Original source | Corrected source |
| --- | --- | --- |
| No recorded gap: retain the observed transition | Pass | Pass |
| Recorded disconnect: do not invent a transition | Fail | Pass |

The tests also require unchanged input arrays, RMS and MAV of 1, valid fraction of 1, and a 75 ms window midpoint. Generation on the corrected source passes three native cases: these two retained cases plus an unchanged smoke test. The paired regression has two total passes and one failure before, then three passes after. TestPilot matches exactly one retained failure-to-pass witness, with no unmatched cases and zero model calls for the comparison.

## Exact source identities

- CaptureSuite original: [3960c0c756cd4e9facbde0d76eaaa3c31ab7c167](https://github.com/Jacob-Met/CaptureSuite/commit/3960c0c756cd4e9facbde0d76eaaa3c31ab7c167).
- CaptureSuite correction: [95ae1955dcff15c7cc4df77ebe66817dbc9b8094](https://github.com/Jacob-Met/CaptureSuite/commit/95ae1955dcff15c7cc4df77ebe66817dbc9b8094).
- TestPilot received toolkit: [a5c292bc9f9f3e05b88bb3feee94cfb7159e4a15](https://github.com/Jacob-Met/testpilot/commit/a5c292bc9f9f3e05b88bb3feee94cfb7159e4a15).

`SOURCE_PROVENANCE.json` maps the exact 80-file Python package subset for each CaptureSuite pin. Only `features/emg.py` differs. The bundle adds a receiving pytest configuration, an unchanged smoke test, source mapping and GPL license. Its local fixture commits are **968723943b234fee81b1d2ee644fa95038313c64** and **a95c709541755cefbcad2b462b9284692b33436a**. These are local fixture identities; they are not the original full CaptureSuite repository commits.

`receive_capture_emg_with_testpilot.py` can reproduce the complete generation step when supplied the two original source checkouts, the toolkit, the project interpreter, GPL license and a fresh output directory. Run its `--help` for parameters. The shorter bundled replay above requires only the delivered toolkit and prepared interpreter.

## Evidence and limits

The first receiver completed both native CLI commands successfully, then stopped on an incorrect post-run assertion that omitted the unchanged smoke test from total counts. The count-assumption receiver is retained unchanged. The corrected receiver collected the existing reports, distinguished total from retained cases, and verified source/worktree preservation without repeating those native commands. `receiving.json` records this setup correction explicitly. The later fresh-bundle replay independently repeated the retained comparison successfully.

This is a synthetic, in-memory EMG example on exact public feature source. It is not an MCAP ingestion, Windows, hardware, physiological or installed-deployment result. Fixed responses establish workflow behavior, not live-model test-generation quality. The Git bundle is a complete history of this small source fixture, not a full repository clone. The earlier scientific and native CaptureSuite evidence remains in its own immutable delivery packets.

The historical fresh-replay receipt names its 80-file count `source_package_bytes_verified`; it checks the bytes of 80 files, not 80 bytes. The reusable replay now names that metadata `source_package_files_verified`. The actually executed helper is preserved alongside the historical receipt; this label-only correction did not repeat native execution.
