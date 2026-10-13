# TestPilot accepted wheel — Windows receiving

This companion records one actual installed-wheel run on original MSI device edc358ed-5ad6-4036-b7aa-8667bf0e14e0, user jacob, Windows 11 build 26200, C:\Python314\python.exe 3.14.3. It qualifies the unchanged source d2596c1a4be11072344c4ea98752cce789865ec4, tree 3b6d270f655310fa2f98cab9bccffca23ec146cf, from Jacob-Met/testpilot. It makes no current-main or maintained-suite claim.

## Start with the accepted kit

[Download the unchanged v2 kit](https://drive.google.com/file/d/1B2lGm_l5bApgUDNqc4SL9B1szHETfIge/view), then use the Windows commands below. The [existing installation guide](https://drive.google.com/file/d/1t7K9EJj6GARw6bw-8OvDl3gpdh6sXuLo/view) and [original cloud/ThinkPad record](../scripted-wheel-1caa1d8e028a/README.md) retain the earlier courses. This companion closes the Windows use gap for that exact artifact; it does not refresh the package to later TestPilot commits.

The [accepted source](https://github.com/Jacob-Met/testpilot/tree/d2596c1a4be11072344c4ea98752cce789865ec4) and its original sample are unchanged. The [complete native companion](native-receiving.zip) includes all four actual saved report/patch files as well as the commands, raw outputs and native receipt. The ZIP contains synthetic sample results only and can be inspected without running TestPilot.

## Accepted input

Use the previously delivered TestPilot-Scripted-Review-d2596c1a-20261013-v2.zip: 107,866 bytes, SHA256 8b3c856751ae9bd24b74474b68624e38e97d9157429aafc6c9d671676be00a4d. All 31 extracted members, 30 manifest payloads and CRC were checked before use. The original ZIP remains immutable in this receiving capsule as kit-v2.zip; it is not duplicated inside this evidence companion.

The contained testpilot-0.1.0-py3-none-any.whl is 75,206 bytes, SHA256 c471d961e1b26051209b2d8bdcf0629b1f0185b25ae6c0d0d733bacca344d246. Its version alone does not identify the accepted source. Every one of the 14 installed modules matched its published Git blob and SHA256 before and after execution.

## Windows prerequisites and commands

The existing pytest 9.0.2 is in Jacob's Python314 user site. The ordinary new virtual environment with --system-site-packages can import it. Python -I hides that user site on this machine, so these Windows commands deliberately omit -I. No dependency copying, .pth addition or dependency download was needed. Stop if the pytest check fails; this companion does not install missing dependencies.

In Command Prompt, from a fresh complete extraction of the accepted kit, choose a new environment and output directory:

```bat
set PYTHONPATH=
set PYTHONHOME=
set PYTHONNOUSERSITE=
set PYTHONDONTWRITEBYTECODE=1
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
C:\Python314\python.exe -B -m venv --system-site-packages testpilot-review
testpilot-review\Scripts\python.exe -B -c "import pytest; print(pytest.__version__); assert int(pytest.__version__.split('.')[0]) >= 8"
testpilot-review\Scripts\python.exe -B -m pip install --no-index --no-deps --no-cache-dir --no-compile testpilot-0.1.0-py3-none-any.whl
testpilot-review\Scripts\python.exe -B -m testpilot --help
testpilot-review\Scripts\python.exe -B -m testpilot targets --repo sample/repo --diff sample/change.diff --json
testpilot-review\Scripts\python.exe -B -m testpilot run --repo sample/repo --diff sample/change.diff --backend scripted --script sample/script --out sample-result --no-coverage
```

The actual receiving controller invoked these interpreter/CLI operations with argument lists rather than through Command Prompt. Its full commands, working directory, raw streams and PIDs are retained. It cleared inherited Python path, TestPilot/provider and credential-like environment overrides without recording their values, disabled unrelated pytest plugin autoload, and directed temporary work into the new capsule. No live backend or provider was used.

## Observed outcome

The seven operations exited 0, 0, 0, 0, 0, 0, 1: environment creation, pytest import, wheel installation, installed-module location check, help, target preview, scripted sample. The final exit 1 is the expected demonstration result: suspected_code_bug, 3 failed and 3 passed cases, including 4 generated cases (1 passed, 3 failed). JUnit was available; no timeout occurred. No proposed patch was applied.

The target preview JSON and generated test contents match the recorded cloud case. Patch text matches after normal native newline decoding; the raw Windows patch bytes are retained separately. Runtime timings, platform diagnostics and native newlines differ, so the full native reports are not claimed byte-identical to cloud outputs.

All four actual outputs are included under sample-result/: report.html, report.json, report.md and testpilot.patch. Open the HTML as a saved report or inspect the JSON and patch. No browser rendering was performed in this receiving course.

All 36 input guards (31 kit members, original ZIP, transport text, controller, accepted-source pins and base interpreter) and all 14 installed-module byte/metadata guards were unchanged. Temporary fixtures were cleaned by the completed course. The venv and reports remain in C:\Users\jacob\hamon-testpilot-wheel-windows-1caa1d8e028a.

## Evidence and bounds

receiving/receipt.json binds every raw operation, exact native paths and source guards. controller.py is the as-run receiver. routing.json preserves the connected device, staging and completed controller PID 145988. source manifests retain the accepted historical pins. The outer MANIFEST.json binds every evidence payload.

This is isolated native qualification of an accepted wheel and its original synthetic example. It does not establish installed estate adoption, current-source compatibility, live model quality, timeout/interrupt behavior, browser usability or a full test-suite pass. Publication/disposition belongs to the existing project delivery handoff; this receipt changes no source, workflow, shared Python installation or review gate.

## Independent delivery review

[independent-review.json](independent-review.json) records read-only checks of all 27 archive members, 26 payload bindings, 25 fresh canonical source pins, all 31 kit members, 36 native input guards and 14 installed-module guards. The seven raw operation pairs and actual report cases were checked independently. No native process or product test was repeated during review.

The immutable native archive is 41,361 bytes, SHA256 `306534cd2d94ecf32dca64013da75f54868bb7868a79720e1b1afd14c73fedee`. [export-custody.json](export-custody.json) binds the completed native export and exact cloud readback. The preliminary isolated-Python capability probe retains its start/output response without a separate completion response in this packet; the actual consumer, archive-export and archive-readback completions are present. This limitation does not replace or broaden the recorded Windows result.

`review_artifact.py` and `fresh-git-pins.json` preserve the as-run cloud artifact verification and exact reference pins. That review script uses its recorded cloud file locations; it is not the product installation entry point. Use the commands above for the unchanged wheel.
