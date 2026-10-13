# TestPilot — installed scripted sample

This kit is an unchanged-source review build from commit
d2596c1a4be11072344c4ea98752cce789865ec4 in Jacob-Met/testpilot.

It lets you install the existing Python package and exercise one original,
deterministic sample without cloning the repository or contacting a model.
The example deliberately contains a broken clamp function. A successful
demonstration ends with exit 1 and status suspected_code_bug, retaining the
failing generated tests for review. It does not claim a passing patch or model
quality.

## Requirements and installation

Use Python 3.12 or newer and an already available pytest 8 or newer. The wheel
does not bundle Python, pytest, or optional coverage. This kit installs no
dependencies from the network.

Extract the complete ZIP into a new folder. Open a terminal there. On Linux or
macOS, create a separate review environment that can see your existing system
packages, check pytest, and install the local wheel:

```sh
python3 -m venv --system-site-packages testpilot-review
testpilot-review/bin/python -I -m pytest --version
testpilot-review/bin/python -m pip install --no-index --no-deps testpilot-0.1.0-py3-none-any.whl
testpilot-review/bin/python -I -m testpilot --help
```

Stop if Python, venv, pip or pytest is unavailable; this packet does not install
those prerequisites. A separately prepared virtual environment with Python and
pytest is also suitable. On Windows the corresponding environment interpreter
is testpilot-review/Scripts/python.exe. Windows and macOS execution are not
qualified by the adjacent cloud receiving evidence.

The package keeps the repository's version 0.1.0. Identify this build by its
source commit and wheel hash, rather than by that shared version alone. Do not
replace another installed TestPilot environment to try this packet.

## Preview and run the original sample

Run from the extracted kit directory:

```sh
testpilot-review/bin/python -I -m testpilot targets --repo sample/repo --diff sample/change.diff --json
testpilot-review/bin/python -I -m testpilot run --repo sample/repo --diff sample/change.diff --backend scripted --script sample/script --out sample-result --no-coverage
```

Choose a new output directory for each result you want to keep. A valid run can
replace an existing report set; the sample-result name is only an example.

The preview selects the changed clamp function. The scripted run executes real
pytest in temporary copies, observes the broken clamp behavior, and keeps the
test failures when the original scripted repair response diagnoses a code bug.
Expected final result: suspected_code_bug, exit 1; 3 failed and 3 passed cases,
including 4 generated cases. The two existing tests remain in the run.

Open sample-result/report.html, or read report.md and report.json. The exact
generated tests are retained in testpilot.patch. Inspect those outputs before
any application of a patch. The sample input files remain unchanged.

This packet also includes the unchanged original fix/calc.py as source
reference within sample/. The commands above do not apply that fix. The
recorded-result/ directory contains the actual cloud run's four complete
outputs, so it can be opened even before installing the package.

## Exact source and evidence

Source: https://github.com/Jacob-Met/testpilot/tree/d2596c1a4be11072344c4ea98752cce789865ec4

Wheel: testpilot-0.1.0-py3-none-any.whl
75,206 bytes
SHA256 c471d961e1b26051209b2d8bdcf0629b1f0185b25ae6c0d0d733bacca344d246

SOURCE_MANIFEST.json identifies every original module, packaging input and sample
file by Git blob and SHA256. All 14 wheel modules match the accepted source.
MANIFEST.json identifies the complete kit. LICENSE contains the original
Apache-2.0 license.

receiving/ contains the complete build and install logs, exact installed
consumer commands and their outputs. Cloud receiving used Python 3.12.14,
pytest 9.1.1, setuptools 84.0.0 and wheel 0.48.0. The new isolated environment
read its existing pytest dependency provider through a receiving-only .pth
file; that local wiring is not included in this distribution. No dependency
download or provider request was required.

Qualification is bounded to the installed package, help, target preview and
this original scripted example. It does not substitute for all maintained
tests, live model validation, browser visual review or installed estate
adoption. Native receiving, when available, is a separate companion receipt.
No product source, workflow or hosted release is changed by this kit.

