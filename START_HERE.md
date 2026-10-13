# TestPilot received toolkit

This folder is a complete Python package for trying the received TestPilot
generation workflow. It combines bounded native output, the copied-project
configuration fix and optional live progress, while retaining the newer main
comparison-console behavior. The current-main refresh also adds a package-version
query and retryable recheck report staging. License and notice files are included.

Use a Python 3.12 environment with pytest 8 or newer installed; this combined
package was received with pytest 9.1.1. Coverage measurement is
optional; the demonstration disables it for generation and uses the established
native recheck behavior. Git is required for the saved-patch adoption step. No
provider account or API key is needed for the included fixed-response demo.

From this folder, check the command:

```sh
python -m testpilot --version
python -m testpilot --help
python -m testpilot run --help
```

Then exercise the complete synthetic workflow in a new directory outside this
folder:

```sh
python -B docs/receiving/composed-toolkit-7cb7e049e2c0/receive_composed_testpilot.py \
  --source . --out /path/to/new-testpilot-review
```

The output contains generated `report.json`, `report.md`, `report.html` and
`testpilot.patch`, followed by an adopted project and an exact-test recheck.
Open `generated/report.html` for the generation result and
`recheck/recheck.html` for the model-free verification. The receiver also saves
phase output and an exact receipt. A successful receiving ends with `ACCEPT` in
that receipt.

The fixture intentionally places a restrictive pytest configuration above its
native temporary directory. The received tool still admits all three expected
tests, retains the last diagnostic after 16 MiB of native output per run, makes
one repair and rechecks the saved patch with zero model calls. Its original
project and pre-existing adopted files remain unchanged.

For an ordinary live-progress run with your selected project and fixed-response
directory, remain in this toolkit folder and use:

```sh
python -m testpilot run --repo /path/to/project --git-base HEAD \
  --backend scripted --script /path/to/responses --progress \
  --out /path/to/new-review
```

If invoking from another folder, set `PYTHONPATH` to this toolkit's absolute
directory so Python selects these received modules. Start with an explicitly
prepared environment and an output directory appropriate for your project.
Existing TestPilot source/test execution limitations still apply.

The full source provenance, actual receiving and limits are in
`docs/receiving/composed-toolkit-7cb7e049e2c0/README.md`; the specific behavior
guides are in `docs/LIVE_PROGRESS.md`, `docs/BOUNDED_TEST_OUTPUT.md`,
`docs/PYTEST_CONFIGURATION_BOUNDARY.md` and `docs/INTERRUPTION_RECEIVING.md`.

The current-main refresh and its precise failure/retry limits are documented in
`docs/receiving/toolkit-refresh-7cb7e049e2c0/README.md`. The package version remains
0.1.0; identify this composed build by its source commit and hashes. Earlier
full generation evidence retains its original attribution.
