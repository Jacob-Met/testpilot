# Complete reports for undecodable filenames

Contributor: `estate-b0e250296538 / live_coordination`. Scope: [TestPilot #2 comment6056837035](https://github.com/Jacob-Met/testpilot/issues/2#issuecomment-6056837035). This receives the concrete reporting failure recorded by the prior independent source-boundary receiver in [comment6056586653](https://github.com/Jacob-Met/testpilot/issues/2#issuecomment-6056586653). The original generated-test preservation contribution is already integrated; its code and ownership are preserved.

## Product failure and correction

A valid POSIX filename can contain a byte that is not valid UTF-8. Python represents that undecodable byte as a surrogate character when decoding the filesystem path. TestPilot already retains that exact filename through Git parsing and source selection. Its final Markdown renderer also inserted that character directly, so writing `report.md` raised `UnicodeEncodeError` after the patch and JSON files had been written. A successful generated test run could therefore leave an empty Markdown report and make output publication raise an exception.

The sole runtime change is in `testpilot/loop.py::render_report`: render the existing report, then convert it to valid UTF-8 while representing unencodable surrogate characters as visible backslash escapes. For example, filesystem-decoded `module` + raw byte `ff` + `.py` is displayed as `module\udcff.py`. Ordinary Unicode such as `café`, `雪`, and emoji stays unchanged. The underlying result and JSON keep the original path identity; generated patch bytes and test outcomes are unchanged. Because the renderer itself returns valid UTF-8 text, both the Markdown writer and CLI display receive the corrected representation.

This is a reporting repair. It does not add arbitrary-byte support to coverage, change pytest outcomes, modify input repositories, or change generated-test allocation/repair behavior.

## Exact receiving source

Initial baseline was main `ca2e6c72743c5d3866f3f14189f1d4c3405f60bf`. During receiving, main advanced to `f350150259c00dd25c43a95d65157022612d15a8`, tree `1fabd676af1bf4cc8c396fc1962b2ea1bc618b66`, including the peer timeout, match/case and project-Python CLI changes. All six changed runtime/test files were materialized exactly into separate current-source receiving copies before final verification. The report-writing baseline itself remained unchanged.

| File / boundary | Identity |
| --- | --- |
| Original `loop.py` Git blob | `e94ae5a0ae3f74fdaa7a63dea73f22e50afbe676` |
| Original `loop.py` SHA-256 | `dd79fbfbdcab00978b288835645c1b5adf37fec404ec0fa6da0ac41d45a79cbf` |
| Candidate `loop.py` Git blob | `dd8270d315b02788f0c177cbf49a802b4f0346fa` |
| Candidate `loop.py` SHA-256 | `d664e0037d99ac8fd2526521afc9437044d26dd389ca31d750f19e6ab248d323` |
| Final regression SHA-256 | `1dde3e4f3b227918e541e4ffc71099a8f36c235c198169bb1a152302ea635a3e` |

AST comparison identifies `render_report` as the only changed top-level definition. Every other runtime module is byte-identical to the receiving main. [source-provenance.json](source-provenance.json) records these comparisons, and [runtime.patch](runtime.patch) contains the exact small runtime delta. The root README, preservation and alias handling, diff selection, sandbox/coverage policy, model routing, browser demo and CI source remain unchanged.

## Native verification

Environment: Python `3.12.14`, pytest `9.1.1`, coverage `7.16.2`, POSIX. The tests use authored disposable Git repositories and ScriptedModel replies, actual pytest/coverage subprocesses, real output files, and actual Git patch application. No live model/provider or private repository data was used. An existing interpreter environment was reused without installation or modification; all test/source working data was isolated under the contribution's own directory.

| Check on exact current receiving source | Result |
| --- | --- |
| Frozen final regression module on original runtime | **6 failed, 1 passed** in 1.67 seconds. |
| Candidate: final regression plus existing loop and generated-test preservation suites | **38 passed**, zero skips, in 14.49 seconds. |
| Valid Unicode and literal escape text | Retained unchanged. |
| Filesystem path, message and model-label surrogates | Visible escapes; valid UTF-8 output; input result unchanged. |
| JSON identity and patch bytes | Preserved across output writing. |
| Successful actual pytest workflow, coverage explicitly disabled through the public API | Two passing tests; complete report; generated patch applies and the receiving repository passes two tests; original module and CRLF test bytes unchanged. |
| Actual default CLI with coverage installed | Coverage's filename failure remains `failed`, runner return 1, CLI exit 1; complete Markdown and CLI output replace the second reporting traceback. |

The new regression does not require coverage to keep its current limitation forever. It requires the CLI status to match the actual runner result and readable reporting in either outcome. In this recorded environment, coverage fails while storing the surrogate-containing filename in SQLite, even though both individual pytest cases pass. The reporting repair preserves that failure instead of producing a false green result.

The final baseline failures remain in [receiving-baseline-tests.log](receiving-baseline-tests.log). [receiving-candidate-tests.log](receiving-candidate-tests.log) records the complete 38-test receiving run. Adjacent run receipts bind commands, exact source/test digests and the receiving commit. Earlier preliminary runs are retained in the contributor's source workspace but are not added to these final result counts.

## Actual before/after artifacts

[current-receiving-summary.json](current-receiving-summary.json) compares the two real workflows:

| Workflow | Original report | Repaired report | Outcome retained |
| --- | ---: | ---: | --- |
| Public API, successful pytest | 0-byte Markdown; output writer raises | 756-byte readable Markdown | `passed`, two tests pass, runner return 0 |
| Public CLI, coverage filename failure | 0-byte Markdown, 948-byte stderr traceback, no stdout | 950-byte readable Markdown, empty stderr, 962-byte stdout | `failed`, two individual cases pass, runner return 1 and CLI exit 1 |

All four generated patches have the same SHA-256: `3e42a3c5abbfbc4da8e28e83f5c08ad4fe64d7ad6f72564f581dbdd29f16f7a0`.

The complete original and repaired `report.json`, `report.md`, and `testpilot.patch` files are under [receiving-baseline-artifacts/](receiving-baseline-artifacts/) and [receiving-candidate-artifacts/](receiving-candidate-artifacts/). Their CLI subdirectories also preserve the real Git-generated diff and the two authored model replies. The adjacent structured API/CLI receipts include runner output and the concrete exception/success evidence. The zero-byte original reports are intentionally preserved negative evidence.

## Reproduction and receiving action

With pytest and coverage available in the chosen Python environment, run from the repository root:

```sh
python -m pytest -q -p no:cacheprovider \
  tests/test_report_text_encoding.py \
  tests/test_loop.py \
  tests/test_generated_test_preservation.py
```

The two raw-filename workflows explicitly require POSIX; the CLI coverage case also requires coverage. Neither is skipped in the retained run. The test module can save structured workflow records when `TESTPILOT_REPORT_RECEIVING_EVIDENCE` names an isolated output directory. The full-repository/eval suite and Windows execution are not claimed by this scoped receiving run.

The source PR should preserve the exact reviewed runtime/regression and unrelated current-main leaves. Its reviewer can inspect the small renderer change, the original failures, the successful patch receiving workflow, and the preserved failed coverage outcome. Integration through that source PR is separate from installed-estate adoption; no service, release pointer, account, or provider state was changed.
